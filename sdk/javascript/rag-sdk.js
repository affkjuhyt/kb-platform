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
  }

  /**
   * Make HTTP request
   * @private
   */
  async _request(method, endpoint, data = null, requiresAuth = true) {
    const url = `${this.baseUrl}${endpoint}`;
    
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

    try {
      const fetchOptions = {
        method,
        headers,
        signal: controller.signal
      };

      if (data && (method === 'POST' || method === 'PUT')) {
        fetchOptions.body = JSON.stringify(data);
      }

      const response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After')) || 60;
        throw new RateLimitError('Rate limit exceeded', retryAfter);
      }

      // Handle other errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new RAGError(
          errorData.detail || `HTTP ${response.status}`,
          response.status,
          errorData
        );
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return null;

    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        throw new RAGError('Request timeout');
      }
      
      throw error;
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
  async login(email, password) {
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

      return this.tokenInfo;

    } catch (error) {
      if (error.statusCode === 401) {
        throw new AuthenticationError('Invalid credentials');
      }
      throw error;
    }
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

    return await this._request('POST', '/query/extract', {
      query,
      tenant_id: this.tenantId,
      schema,
      top_k: topK,
      min_confidence: minConfidence
    });
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
