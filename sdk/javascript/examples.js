/**
 * Example usage of RAG JavaScript SDK
 * 
 * This file demonstrates various use cases for the RAG JavaScript SDK.
 * 
 * Usage:
 *   node examples.js
 * 
 * Or in browser:
 *   <script src="rag-sdk.js"></script>
 *   <script src="examples.js"></script>
 */

// For Node.js, import the SDK
// const { RAGClient } = require('./rag-sdk.js');

// Examples
const examples = {
  
  /**
   * Example 1: Basic usage with login
   */
  async basicUsage() {
    console.log('\n=== Example 1: Basic Usage ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant'
    });
    
    try {
      // Login
      const token = await client.login('user@example.com', 'password');
      console.log(`✓ Logged in. Token expires in ${token.expiresIn} seconds`);
      
      // Health check
      const health = await client.healthCheck();
      console.log(`✓ API Health: ${health.status}`);
      
    } catch (error) {
      if (error.name === 'AuthenticationError') {
        console.log(`✗ Authentication failed: ${error.message}`);
      } else {
        console.log(`✗ Error: ${error.message}`);
      }
    }
  },

  /**
   * Example 2: Using API key authentication
   */
  async apiKeyAuth() {
    console.log('\n=== Example 2: API Key Authentication ===');
    
    // No login needed with API key
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    try {
      // Directly use search without login
      const results = await client.search('machine learning', { topK: 3 });
      console.log(`✓ Found ${results.length} results using API key`);
      
    } catch (error) {
      console.log(`✗ API error: ${error.message}`);
    }
  },

  /**
   * Example 3: RAG query with citations
   */
  async ragQuery() {
    console.log('\n=== Example 3: RAG Query ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    try {
      const response = await client.ragQuery('What is machine learning?', {
        topK: 5,
        sessionId: 'session-001'
      });
      
      console.log(`✓ Answer: ${response.answer}`);
      console.log(`  Confidence: ${response.confidence.toFixed(2)}`);
      console.log(`  Citations: ${response.citations.length}`);
      
      response.citations.slice(0, 3).forEach((citation, i) => {
        console.log(`    ${i + 1}. ${citation.doc_id} (source: ${citation.source})`);
      });
      
    } catch (error) {
      console.log(`✗ API error: ${error.message}`);
    }
  },

  /**
   * Example 4: Structured data extraction
   */
  async dataExtraction() {
    console.log('\n=== Example 4: Data Extraction ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    // Define extraction schema
    const schema = {
      type: 'object',
      properties: {
        company_name: {
          type: 'string',
          description: 'Name of the company'
        },
        founded_year: {
          type: 'integer',
          description: 'Year the company was founded'
        },
        headquarters: {
          type: 'string',
          description: 'Location of headquarters'
        },
        employees: {
          type: 'integer',
          description: 'Number of employees'
        }
      },
      required: ['company_name']
    };
    
    try {
      const result = await client.extract(
        'Extract company information from the about page',
        schema,
        { topK: 5, minConfidence: 0.7 }
      );
      
      if (result.success) {
        console.log('✓ Extraction successful');
        console.log(`  Confidence: ${result.confidence.toFixed(2)}`);
        console.log(`  Data: ${JSON.stringify(result.data, null, 2)}`);
      } else {
        console.log('✗ Extraction failed');
        console.log(`  Errors: ${result.validationErrors.join(', ')}`);
      }
      
    } catch (error) {
      console.log(`✗ API error: ${error.message}`);
    }
  },

  /**
   * Example 5: Async extraction with job tracking
   */
  async asyncExtraction() {
    console.log('\n=== Example 5: Async Extraction ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    const schema = {
      type: 'object',
      properties: {
        employees: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              email: { type: 'string' },
              department: { type: 'string' }
            }
          }
        }
      }
    };
    
    try {
      console.log('Starting async extraction...');
      const result = await client.extractWithJob(
        'Extract all employee information',
        schema,
        {
          schemaName: 'employee_list',
          topK: 10,
          pollInterval: 2000,
          maxWait: 60000
        }
      );
      
      if (result.success) {
        console.log('✓ Async extraction completed');
        console.log(`  Job ID: ${result.jobId}`);
        console.log(`  Found ${result.data.employees?.length || 0} employees`);
      } else {
        console.log('✗ Async extraction failed');
        console.log(`  Errors: ${result.validationErrors.join(', ')}`);
      }
      
    } catch (error) {
      console.log(`✗ API error: ${error.message}`);
    }
  },

  /**
   * Example 6: Error handling
   */
  async errorHandling() {
    console.log('\n=== Example 6: Error Handling ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant'
    });
    
    try {
      // Try to search without authentication
      await client.search('test');
      
    } catch (error) {
      if (error.name === 'AuthenticationError') {
        console.log(`✓ Caught authentication error: ${error.message}`);
      } else if (error.name === 'RateLimitError') {
        console.log(`✓ Caught rate limit error: ${error.message}`);
        console.log(`  Retry after: ${error.retryAfter} seconds`);
      } else if (error.name === 'RAGError') {
        console.log(`✓ Caught API error: ${error.message}`);
        console.log(`  Status code: ${error.statusCode}`);
      } else {
        console.log(`✗ Unexpected error: ${error.message}`);
      }
    }
  },

  /**
   * Example 7: Multi-turn conversation with session
   */
  async conversationSession() {
    console.log('\n=== Example 7: Conversation Session ===');
    
    const sessionId = `session-${Date.now()}`;
    console.log(`Session ID: ${sessionId}`);
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    const questions = [
      'What is machine learning?',
      'What are the types of machine learning?',
      'Give me an example of supervised learning.'
    ];
    
    for (let i = 0; i < questions.length; i++) {
      try {
        const response = await client.ragQuery(questions[i], { sessionId });
        
        console.log(`\nQ${i + 1}: ${questions[i]}`);
        console.log(`A${i + 1}: ${response.answer.substring(0, 100)}...`);
        
      } catch (error) {
        console.log(`✗ Error in turn ${i + 1}: ${error.message}`);
      }
    }
  },

  /**
   * Example 8: Batch search operations
   */
  async batchSearch() {
    console.log('\n=== Example 8: Batch Search ===');
    
    const queries = [
      'machine learning',
      'deep learning',
      'neural networks',
      'natural language processing'
    ];
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    for (const query of queries) {
      try {
        const results = await client.search(query, { topK: 3 });
        console.log(`✓ '${query}': ${results.length} results`);
        
      } catch (error) {
        console.log(`✗ '${query}': Error - ${error.message}`);
      }
    }
  },

  /**
   * Example 9: Quick convenience functions
   */
  async quickFunctions() {
    console.log('\n=== Example 9: Quick Functions ===');
    
    // Note: These functions require the SDK to be imported
    // const { search, ragQuery } = require('./rag-sdk.js');
    
    const config = {
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    };
    
    try {
      // Quick search
      // const results = await search(config, 'machine learning', { topK: 5 });
      console.log('✓ Quick search: (uncomment to run)');
      
      // Quick RAG query
      // const answer = await ragQuery(config, 'What is AI?');
      console.log('✓ Quick RAG: (uncomment to run)');
      
    } catch (error) {
      console.log(`✗ Error: ${error.message}`);
    }
  },

  /**
   * Example 10: Using with async/await and Promise.all
   */
  async parallelRequests() {
    console.log('\n=== Example 10: Parallel Requests ===');
    
    const client = new RAGClient({
      baseUrl: 'http://localhost:8000',
      tenantId: 'demo-tenant',
      apiKey: 'rag_your_api_key_here'
    });
    
    const queries = [
      'machine learning basics',
      'deep learning introduction',
      'neural networks explained'
    ];
    
    try {
      console.log('Running parallel searches...');
      
      // Execute searches in parallel
      const promises = queries.map(query => 
        client.search(query, { topK: 3 })
          .then(results => ({ query, results, success: true }))
          .catch(error => ({ query, error: error.message, success: false }))
      );
      
      const results = await Promise.all(promises);
      
      results.forEach(({ query, results, error, success }) => {
        if (success) {
          console.log(`✓ '${query}': ${results.length} results`);
        } else {
          console.log(`✗ '${query}': ${error}`);
        }
      });
      
    } catch (error) {
      console.log(`✗ Error: ${error.message}`);
    }
  }

};


// Run examples
async function runExamples() {
  console.log('=' .repeat(70));
  console.log('RAG SDK JavaScript Examples');
  console.log('=' .repeat(70));
  
  const exampleList = [
    examples.basicUsage,
    examples.apiKeyAuth,
    examples.ragQuery,
    examples.dataExtraction,
    examples.asyncExtraction,
    examples.errorHandling,
    examples.conversationSession,
    examples.batchSearch,
    examples.quickFunctions,
    examples.parallelRequests
  ];
  
  for (const example of exampleList) {
    try {
      await example();
    } catch (error) {
      console.log(`\n✗ Example failed: ${error.message}`);
    }
  }
  
  console.log('\n' + '='.repeat(70));
  console.log('Examples completed!');
  console.log('='.repeat(70));
}

// Run if in Node.js
if (typeof module !== 'undefined' && module.exports) {
  // Export for use as module
  module.exports = examples;
  
  // Run examples if executed directly
  if (require.main === module) {
    runExamples();
  }
}
