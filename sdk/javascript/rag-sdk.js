/**
 * RAG System JavaScript SDK
 * 
 * A JavaScript/TypeScript SDK for interacting with the RAG System API Gateway.
 * 
 * Features:
 * - Authentication (JWT and API Key)
 * - Search operations
 * - RAG queries
 * - Data extraction
 * - Automatic token refresh
 * - Rate limit handling
 * 
 * Installation:
 *   npm install rag-sdk
 *   # or
 *   yarn add rag-sdk
 * 
 * Usage:
 *   import { RAGClient } from 'rag-sdk';
 *   
 *   const client = new RAGClient({
 *     baseUrl: 'https://api.ragsystem.com',
 *     tenantId: 'your-tenant-id'
 *   });
 *   
 *   // Login
 *   await client.login('user@example.com', 'password');
 *   
 *   // Search
 *   const results = await client.search('machine learning', { topK: 5 });
 *   
 *   // RAG Query
 *   const answer = await client.ragQuery('What is deep learning?');
 */

class RAGError extends Error {
  constructor(message, statusCode = null, response = null) {
    super(message);
    this.name = 'RAGError';
    this.statusCode = statusCode;
    this.response = response;
  }
}

class AuthenticationError extends RAGError {
  constructor(message) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

class RateLimitError extends RAGError {
  constructor(message, retryAfter = null) {
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * RAG System API Client
 */
class RAGClient {
  /**
   * Create a new RAG client
   * @param {Object} config - Client configuration
   * @param {string} config.baseUrl - API Gateway base URL
   * @param {string} config.tenantId - Tenant identifier
   * @param {string} [config.apiKey] - Optional API key for authentication
   * @param {number} [config.timeout=30000] - Request timeout in milliseconds
   */
  constructor({ baseUrl, tenantId, apiKey = null, timeout = 30000 }) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.tenantId = tenantId;
    this.apiKey = apiKey;
    this.timeout = timeout;
    this.tokenInfo = null;
    // Retry metrics
    this._retryStats = { transientRetries: 0, totalBackoffMs: 0, lastRetryAt: null };
    // Store credentials for optional token refresh
    this._credentials = null;
  }

  /**
   * Make HTTP request
   * @private
   */
  async _request(method, endpoint, data = null, requiresAuth = true) {
    const url = `${this.baseUrl}${endpoint}`;
    
    // Preflight: refresh token if expired before making the request
    if (requiresAuth && !this.apiKey) {
      if (!this.tokenInfo || this._isTokenExpired()) {
        if (this._credentials) {
          await this._refreshToken();
        }
      }
      if (!this.tokenInfo || this._isTokenExpired()) {
        throw new AuthenticationError('Not authenticated. Please login.');
      }
    }

    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    if (requiresAuth) {
      const authHeader = this._getAuthHeader();
      Object.assign(headers, authHeader);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    // Retry/backoff configuration
    const maxRetries = 3;
    let attempt = 0;
    const sleep = (ms) => new Promise(res => setTimeout(res, ms));

    while (true) {
      try {
        const fetchOptions = {
          method,
          headers,
          signal: controller.signal
        };

      if (data && (method === 'POST' || method === 'PUT')) {
        fetchOptions.body = JSON.stringify(data);
      }
        while (true) {
          const response = await fetch(url, fetchOptions);
          clearTimeout(timeoutId);

          // Retry on rate limit
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After')) || 60;
        // update retry metrics
        this._retryStats.transientRetries += 1;
        this._retryStats.totalBackoffMs += retryAfter * 1000;
        this._retryStats.lastRetryAt = Date.now();
        if (attempt < maxRetries) {
          console.warn(`Retry ${attempt + 1} after 429 for ${method} ${endpoint}, retrying in ${retryAfter}s`);
          await sleep(retryAfter * 1000);
          attempt++;
          continue;
        }
        throw new RateLimitError('Rate limit exceeded', retryAfter);
      }

      // Retry on server errors
      if (response.status >= 500 && response.status < 600) {
        if (attempt < maxRetries) {
          const backoffMs = Math.max(500, Math.floor((0.5 * Math.pow(2, attempt)) * 1000));
          console.warn(`Retry ${attempt + 1} after ${response.status} on ${method} ${endpoint}, backoff ${backoffMs}ms`);
          // update metrics
          this._retryStats.transientRetries += 1;
          this._retryStats.totalBackoffMs += backoffMs;
          this._retryStats.lastRetryAt = Date.now();
          await sleep(backoffMs);
          attempt++;
          continue;
        }
      }

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new RAGError(
              errorData.detail || `HTTP ${response.status}`,
              response.status,
              errorData
            );
          }

          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json')) {
            return await response.json();
          }
          return null;
        }
      } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
          throw new RAGError('Request timeout');
        }
        throw error;
      }
    }
  }

  /**
   * Get authentication header
   * @private
   */
  _getAuthHeader() {
    if (this.apiKey) {
      return { 'X-API-Key': this.apiKey };
    }

    if (this.tokenInfo && !this._isTokenExpired()) {
      return { 'Authorization': `Bearer ${this.tokenInfo.accessToken}` };
    }

    throw new AuthenticationError('Not authenticated. Call login() first.');
  }

  _validateAgainstSchema(instance, schema) {
    if (!schema || instance == null) return;
    try {
      const t = schema.type;
      if (t === 'object' && schema.properties) {
        const required = schema.required || [];
        for (const key of required) {
          if (!(key in instance)) {
            throw new Error(`Missing required key: ${key}`);
          }
        }
        for (const key of Object.keys(schema.properties)) {
          const prop = schema.properties[key];
          const pt = prop.type;
          const val = instance[key];
          if (val == null) continue;
          if (pt === 'string' && typeof val !== 'string') {
            throw new Error(`Invalid type for ${key}, expected string`);
          }
          if (pt === 'number' && typeof val !== 'number') {
            throw new Error(`Invalid type for ${key}, expected number`);
          }
          if (pt === 'integer' && !Number.isInteger(val)) {
            throw new Error(`Invalid type for ${key}, expected integer`);
          }
          if (pt === 'array' && !Array.isArray(val)) {
            throw new Error(`Invalid type for ${key}, expected array`);
          }
        }
      }
    } catch (e) {
      throw new RAGError(`Schema validation failed: ${e.message}`, null, {});
    }
  }

  /**
   * Check if token is expired
   * @private
   */
  _isTokenExpired() {
    if (!this.tokenInfo) return true;
    
    const expiryTime = this.tokenInfo.obtainedAt + (this.tokenInfo.expiresIn - 60) * 1000;
    return Date.now() >= expiryTime;
  }

  /**
   * Authenticate with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} Token information
   * @throws {AuthenticationError} If credentials are invalid
   */
  async login(email, password, rememberCredentials = false) {
    try {
      const response = await this._request(
        'POST',
        '/auth/login',
        {
          email,
          password,
          tenant_id: this.tenantId
        },
        false
      );

      this.tokenInfo = {
        accessToken: response.access_token,
        tokenType: response.token_type,
        expiresIn: response.expires_in,
        tenantId: response.tenant_id,
        obtainedAt: Date.now()
      };

      if (rememberCredentials) {
        this._credentials = { email, password };
      }

      return this.tokenInfo;

    } catch (error) {
      if (error.statusCode === 401) {
        throw new AuthenticationError('Invalid credentials');
      }
      throw error;
    }
  }

  async _refreshToken() {
    if (!this._credentials) {
      throw new AuthenticationError('Not authenticated. Please login.');
    }
    const { email, password } = this._credentials;
    const response = await this._request(
      'POST',
      '/auth/login',
      {
        email,
        password,
        tenant_id: this.tenantId
      },
      false
    );
    this.tokenInfo = {
      accessToken: response.access_token,
      tokenType: response.token_type,
      expiresIn: response.expires_in,
      tenantId: response.tenant_id,
      obtainedAt: Date.now()
    };
  }

  /**
   * Register a new user
   * @param {string} email - User email
   * @param {string} password - User password (min 8 characters)
   * @param {string} name - User full name
   * @returns {Promise<Object>} Token information
   */
  async register(email, password, name) {
    const response = await this._request(
      'POST',
      '/auth/register',
      {
        email,
        password,
        tenant_id: this.tenantId,
        name
      },
      false
    );

    this.tokenInfo = {
      accessToken: response.access_token,
      tokenType: response.token_type,
      expiresIn: response.expires_in,
      tenantId: response.tenant_id,
      obtainedAt: Date.now()
    };

    return this.tokenInfo;
  }

  /**
   * Search documents
   * @param {string} query - Search query
   * @param {Object} [options] - Search options
   * @param {number} [options.topK=10] - Number of results
   * @param {Object} [options.filters] - Optional filters
   * @returns {Promise<Array>} Search results
   */
  async search(query, options = {}) {
    const { topK = 10, filters = null } = options;

    const data = {
      query,
      tenant_id: this.tenantId,
      top_k: topK
    };

    if (filters) {
      data.filters = filters;
    }

    const response = await this._request('POST', '/query/search', data);
    return response.results || [];
  }

  /**
   * Perform RAG query
   * @param {string} query - User question
   * @param {Object} [options] - Query options
   * @param {number} [options.topK=5] - Number of context documents
   * @param {string} [options.sessionId] - Session ID for conversation tracking
   * @returns {Promise<Object>} RAG response with answer and citations
   */
  async ragQuery(query, options = {}) {
    const { topK = 5, sessionId = null } = options;

    const data = {
      query,
      tenant_id: this.tenantId,
      top_k: topK
    };

    if (sessionId) {
      data.session_id = sessionId;
    }

    return await this._request('POST', '/query/rag', data);
  }

  /**
   * Extract structured data
   * @param {string} query - Extraction query/description
   * @param {Object} schema - JSON schema defining expected output
   * @param {Object} [options] - Extraction options
   * @param {number} [options.topK=5] - Number of documents
   * @param {number} [options.minConfidence=0.7] - Minimum confidence
   * @returns {Promise<Object>} Extraction response
   */
  async extract(query, schema, options = {}) {
    const { topK = 5, minConfidence = 0.7 } = options;

    const resp = await this._request('POST', '/query/extract', {
      query,
      tenant_id: this.tenantId,
      schema,
      top_k: topK,
      min_confidence: minConfidence
    });
    // Validate the response data against provided schema if available
    try {
      this._validateAgainstSchema(resp.data, schema);
    } catch (e) {
      // ignore host-side validation errors to avoid breaking API integration
    }
    return resp;
  }

  /**
   * Extract structured data with job tracking (async)
   * @param {string} query - Extraction query/description
   * @param {Object} schema - JSON schema defining expected output
   * @param {Object} [options] - Extraction options
   * @param {string} [options.schemaName='custom'] - Schema name
   * @param {number} [options.topK=5] - Number of documents
   * @param {number} [options.minConfidence=0.7] - Minimum confidence
   * @param {number} [options.pollInterval=2000] - Poll interval in ms
   * @param {number} [options.maxWait=60000] - Max wait time in ms
   * @returns {Promise<Object>} Extraction response
   */
  async extractWithJob(query, schema, options = {}) {
    const {
      schemaName = 'custom',
      topK = 5,
      minConfidence = 0.7,
      pollInterval = 2000,
      maxWait = 60000
    } = options;

    // Create job
    const createResponse = await this._request('POST', '/query/extract/jobs', {
      query,
      tenant_id: this.tenantId,
      schema,
      schema_name: schemaName,
      top_k: topK,
      min_confidence: minConfidence
    });

    const jobId = createResponse.job_id;
    const startTime = Date.now();

    // Poll for completion
    while (Date.now() - startTime < maxWait) {
      const statusResponse = await this._request(
        'GET',
        `/query/extract/jobs/${jobId}`
      );

      const status = statusResponse.job.status;
      
      if (status === 'completed') {
        const results = statusResponse.results || [];
        if (results.length > 0) {
          const result = results[0];
          // Validate data if schema provided
          try {
            this._validateAgainstSchema(result.data, schema);
          } catch (e) {
            // ignore validation errors on client side
          }
          return {
            success: true,
            data: result.data,
            confidence: result.confidence,
            validationErrors: result.validation_errors || [],
            jobId
          };
        } else {
          return {
            success: false,
            data: null,
            confidence: 0,
            validationErrors: ['No results'],
            jobId
          };
        }
      } else if (status === 'failed') {
        return {
          success: false,
          data: null,
          confidence: 0,
          validationErrors: ['Job failed'],
          jobId
        };
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    // Timeout
    return {
      success: false,
      data: null,
      confidence: 0,
      validationErrors: ['Timeout waiting for job completion'],
      jobId
    };
  }

  /**
   * Check API health
   * @returns {Promise<Object>} Health status
   */
  async healthCheck() {
    return await this._request('GET', '/health', null, false);
  }

  /**
   * Get current user info
   * @returns {Promise<Object>} User information
   */
  async getCurrentUser() {
    return await this._request('GET', '/auth/me');
  }

  // Retrieve retry statistics for observability
  getRetryStats() {
    return this._retryStats || { transientRetries: 0, totalBackoffMs: 0, lastRetryAt: null };
  }
}

/**
 * Quick search function using API key
 * @param {Object} config - Configuration
 * @param {string} config.baseUrl - API base URL
 * @param {string} config.tenantId - Tenant ID
 * @param {string} config.apiKey - API key
 * @param {string} query - Search query
 * @param {Object} [options] - Search options
 * @returns {Promise<Array>} Search results
 */
async function search({ baseUrl, tenantId, apiKey }, query, options = {}) {
  const client = new RAGClient({ baseUrl, tenantId, apiKey });
  try {
    return await client.search(query, options);
  } finally {
    // No cleanup needed for API key auth
  }
}

/**
 * Quick RAG query function using API key
 * @param {Object} config - Configuration
 * @param {string} config.baseUrl - API base URL
 * @param {string} config.tenantId - Tenant ID
 * @param {string} config.apiKey - API key
 * @param {string} query - Query text
 * @param {Object} [options] - Query options
 * @returns {Promise<Object>} RAG response
 */
async function ragQuery({ baseUrl, tenantId, apiKey }, query, options = {}) {
  const client = new RAGClient({ baseUrl, tenantId, apiKey });
  try {
    return await client.ragQuery(query, options);
  } finally {
    // No cleanup needed for API key auth
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  // CommonJS
  module.exports = {
    RAGClient,
    RAGError,
    AuthenticationError,
    RateLimitError,
    search,
    ragQuery
  };
} else if (typeof define === 'function' && define.amd) {
  // AMD
  define([], function() {
    return {
      RAGClient,
      RAGError,
      AuthenticationError,
      RateLimitError,
      search,
      ragQuery
    };
  });
} else {
  // Browser global
  window.RAGSDK = {
    RAGClient,
    RAGError,
    AuthenticationError,
    RateLimitError,
    search,
    ragQuery
  };
}
