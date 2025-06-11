import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Folder, Play, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { useApp } from '../context/AppContext';
import contextService from '../services/contextService';
import styles from './SetupPage.module.css';

const SetupPage = () => {
  const { state, actions } = useApp();
  const navigate = useNavigate();
  const [localCodebasePath, setLocalCodebasePath] = useState(state.codebasePath || '');
  const [validationError, setValidationError] = useState('');

  const validatePath = (path) => {
    if (!path.trim()) {
      return 'Codebase path is required';
    }
    
    // Basic path validation - you can enhance this
    if (!path.includes('/') && !path.includes('\\')) {
      return 'Please enter a valid file system path';
    }
    
    return '';
  };

  const handlePathChange = (e) => {
    const path = e.target.value;
    setLocalCodebasePath(path);
    
    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError('');
    }
  };

  const handleStartProcessing = async () => {
    const error = validatePath(localCodebasePath);
    if (error) {
      setValidationError(error);
      return;
    }

    actions.setError(null);
    actions.setLoading(true);
    actions.setCodebasePath(localCodebasePath);

    try {
      console.log('Starting context gathering for:', localCodebasePath);
      
      const response = await contextService.gatherContext(localCodebasePath);
      
      console.log('Context gathering response:', response);

      if (response.statuscode === 200) {
        actions.setContextGathered(true);
        
        // Short delay to show success state before navigation
        setTimeout(() => {
          navigate('/chat');
        }, 1500);
      } else {
        throw new Error(response.error || 'Failed to gather context');
      }
      
    } catch (error) {
      console.error('Context gathering failed:', error);
      actions.setError(error.response?.data?.error || error.message || 'Failed to process codebase');
    } finally {
      actions.setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !state.isLoading) {
      handleStartProcessing();
    }
  };

  const getStatusIcon = () => {
    if (state.isLoading) {
      return <Clock className={styles.statusIcon} />;
    }
    if (state.error) {
      return <AlertCircle className={styles.statusIcon} />;
    }
    if (state.isContextGathered) {
      return <CheckCircle className={styles.statusIcon} />;
    }
    return <Play className={styles.statusIcon} />;
  };

  const getStatusMessage = () => {
    if (state.isLoading) {
      return 'Processing codebase... This may take a few minutes.';
    }
    if (state.error) {
      return `Error: ${state.error}`;
    }
    if (state.isContextGathered) {
      return 'Context gathering completed! Redirecting to chat...';
    }
    return 'Ready to process your codebase';
  };

  const getStatusClass = () => {
    if (state.isLoading) return styles.statusLoading;
    if (state.error) return styles.statusError;
    if (state.isContextGathered) return styles.statusSuccess;
    return styles.statusReady;
  };

  return (
    <div className={styles.setupPage}>
      <div className="container container-sm">
        <div className={styles.setupContent}>
          <div className={styles.setupHeader}>
            <Folder className={styles.headerIcon} />
            <h1 className={styles.setupTitle}>Setup Your Codebase</h1>
            <p className={styles.setupDescription}>
              Enter the path to your codebase to begin context analysis. The system will 
              process your code files and prepare the context management infrastructure.
            </p>
          </div>

          <div className={`card ${styles.setupCard}`}>
            <div className="card-body">
              <div className="form-group">
                <label htmlFor="codebasePath" className="form-label">
                  Codebase Path *
                </label>
                <input
                  id="codebasePath"
                  type="text"
                  className={`form-input ${validationError ? styles.inputError : ''}`}
                  placeholder="/path/to/your/codebase"
                  value={localCodebasePath}
                  onChange={handlePathChange}
                  onKeyPress={handleKeyPress}
                  disabled={state.isLoading}
                />
                {validationError && (
                  <div className={styles.errorMessage}>
                    <AlertCircle size={16} />
                    {validationError}
                  </div>
                )}
              </div>

              <div className={styles.setupActions}>
                <button
                  className={`btn btn-primary btn-lg ${styles.processButton}`}
                  onClick={handleStartProcessing}
                  disabled={state.isLoading || !localCodebasePath.trim()}
                >
                  {state.isLoading && <div className="spinner" />}
                  {state.isLoading ? 'Processing...' : 'Start Processing'}
                </button>
              </div>
            </div>
          </div>

          <div className={`${styles.statusCard} ${getStatusClass()}`}>
            <div className={styles.statusContent}>
              {getStatusIcon()}
              <div className={styles.statusText}>
                <h3 className={styles.statusTitle}>
                  {state.isLoading ? 'Processing' : 
                   state.error ? 'Error' :
                   state.isContextGathered ? 'Completed' : 'Ready'}
                </h3>
                <p className={styles.statusMessage}>{getStatusMessage()}</p>
                {state.isLoading && (
                  <div className={styles.processingSteps}>
                    <div className={styles.step}>
                      <div className={styles.stepIndicator} />
                      <span>Detecting changes with Merkle tree</span>
                    </div>
                    <div className={styles.step}>
                      <div className={styles.stepIndicator} />
                      <span>Chunking and embedding generation</span>
                    </div>
                    <div className={styles.step}>
                      <div className={styles.stepIndicator} />
                      <span>Updating vector database</span>
                    </div>
                    <div className={styles.step}>
                      <div className={styles.stepIndicator} />
                      <span>Building repository map</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className={styles.setupInfo}>
            <h3>What happens during processing?</h3>
            <ul>
              <li>
                <strong>Change Detection:</strong> The system uses Merkle trees to detect 
                modifications in your codebase efficiently.
              </li>
              <li>
                <strong>Content Analysis:</strong> Files are chunked and processed using 
                advanced embeddings for semantic understanding.
              </li>
              <li>
                <strong>Graph Building:</strong> A comprehensive repository map is created 
                and stored in Neo4j for structural queries.
              </li>
              <li>
                <strong>Context Preparation:</strong> Multiple retrieval tools are prepared 
                for different types of context queries.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SetupPage; 