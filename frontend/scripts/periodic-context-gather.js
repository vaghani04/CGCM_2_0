#!/usr/bin/env node

/**
 * Periodic Context Gathering Script
 * 
 * This script can be run independently to periodically hit the context-gather endpoint.
 * Usage: node scripts/periodic-context-gather.js [codebase-path] [interval-minutes]
 * 
 * Default interval: 3 minutes
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const DEFAULT_INTERVAL_MINUTES = 3;

class PeriodicContextGatherer {
  constructor(codebasePath, intervalMinutes = DEFAULT_INTERVAL_MINUTES) {
    this.codebasePath = codebasePath;
    this.intervalMinutes = intervalMinutes;
    this.intervalMs = intervalMinutes * 60 * 1000;
    this.intervalId = null;
    this.isRunning = false;

    // Create axios instance
    this.apiClient = axios.create({
      baseURL: API_BASE_URL,
      timeout: 300000, // 5 minutes timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Bind methods
    this.start = this.start.bind(this);
    this.stop = this.stop.bind(this);
    this.gatherContext = this.gatherContext.bind(this);
    this.handleExit = this.handleExit.bind(this);

    // Setup graceful shutdown
    process.on('SIGINT', this.handleExit);
    process.on('SIGTERM', this.handleExit);
  }

  async gatherContext() {
    if (this.isRunning) {
      console.log(`[${new Date().toISOString()}] Context gathering already in progress, skipping...`);
      return;
    }

    this.isRunning = true;

    try {
      console.log(`[${new Date().toISOString()}] Starting context gathering for: ${this.codebasePath}`);
      
      const response = await this.apiClient.post('/context-gather', {
        codebase_path: this.codebasePath
      });

      if (response.data && response.data.statuscode === 200) {
        console.log(`[${new Date().toISOString()}] ✅ Context gathering completed successfully`);
        console.log(`   - Status: ${response.data.detail}`);
        console.log(`   - Time taken: ${response.data.time_taken_seconds}s`);
      } else {
        console.log(`[${new Date().toISOString()}] ⚠️  Context gathering completed with warnings`);
        console.log(`   - Response:`, response.data);
      }
    } catch (error) {
      console.error(`[${new Date().toISOString()}] ❌ Context gathering failed:`);
      
      if (error.response) {
        console.error(`   - Status: ${error.response.status}`);
        console.error(`   - Error: ${error.response.data?.error || error.response.statusText}`);
      } else if (error.request) {
        console.error(`   - Network error: Unable to reach server at ${API_BASE_URL}`);
      } else {
        console.error(`   - Error: ${error.message}`);
      }
    } finally {
      this.isRunning = false;
    }
  }

  start() {
    if (this.intervalId) {
      console.log('Periodic context gathering is already running');
      return;
    }

    console.log(`🚀 Starting periodic context gathering...`);
    console.log(`   - Codebase: ${this.codebasePath}`);
    console.log(`   - Interval: ${this.intervalMinutes} minutes`);
    console.log(`   - API URL: ${API_BASE_URL}`);
    console.log(`   - Next run: ${new Date(Date.now() + this.intervalMs).toISOString()}`);
    console.log(`   - Press Ctrl+C to stop\n`);

    // Run immediately on start
    this.gatherContext();

    // Schedule periodic runs
    this.intervalId = setInterval(this.gatherContext, this.intervalMs);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log(`\n🛑 Periodic context gathering stopped`);
    }
  }

  handleExit() {
    console.log('\n⏹️  Shutting down gracefully...');
    this.stop();
    process.exit(0);
  }
}

// CLI Interface
function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Periodic Context Gathering Script

Usage: node scripts/periodic-context-gather.js [codebase-path] [interval-minutes]

Arguments:
  codebase-path     Path to the codebase (required)
  interval-minutes  Interval between context gathering in minutes (default: ${DEFAULT_INTERVAL_MINUTES})

 Environment Variables:
   REACT_APP_API_URL  API base URL (default: http://localhost:8000/api/v1)

Examples:
  node scripts/periodic-context-gather.js /path/to/codebase
  node scripts/periodic-context-gather.js /path/to/codebase 5
     REACT_APP_API_URL=http://localhost:3001/api/v1 node scripts/periodic-context-gather.js /path/to/codebase
    `);
    process.exit(0);
  }

  const codebasePath = args[0];
  const intervalMinutes = parseInt(args[1]) || DEFAULT_INTERVAL_MINUTES;

  if (!codebasePath) {
    console.error('❌ Error: Codebase path is required');
    console.error('Usage: node scripts/periodic-context-gather.js [codebase-path] [interval-minutes]');
    console.error('Run with --help for more information');
    process.exit(1);
  }

  if (intervalMinutes < 1) {
    console.error('❌ Error: Interval must be at least 1 minute');
    process.exit(1);
  }

  const gatherer = new PeriodicContextGatherer(codebasePath, intervalMinutes);
  gatherer.start();
}

// Run if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export default PeriodicContextGatherer; 