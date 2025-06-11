import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, AlertCircle, RefreshCw, MessageSquare } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { usePeriodicContextGather } from '../hooks/usePeriodicContextGather';
import contextService from '../services/contextService';
import styles from './ChatPage.module.css';

const ChatPage = () => {
  const { state, actions } = useApp();
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const chatContainerRef = useRef(null);
  const inputRef = useRef(null);
  
  // Initialize periodic context gathering
  const { isPeriodicGatheringActive } = usePeriodicContextGather();

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [state.chatHistory]);

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim() || isSubmitting || !state.codebasePath) {
      return;
    }

    setIsSubmitting(true);
    actions.setError(null);

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };
    actions.addChatMessage(userMessage);

    const currentQuery = query;
    setQuery('');

    try {
      const response = await contextService.submitUserQuery(currentQuery, state.codebasePath);
      
      if (response.statuscode === 200) {
        // Add assistant response to chat
        const assistantMessage = {
          id: Date.now() + 1,
          type: 'assistant',
          content: response.data,
          timestamp: new Date().toISOString(),
          timeTaken: response.time_taken_seconds
        };
        actions.addChatMessage(assistantMessage);
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Query submission failed:', error);
      actions.setError(error.response?.data?.error || error.message || 'Failed to process query');
      
      // Add error message to chat
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: error.response?.data?.error || error.message || 'Failed to process query',
        timestamp: new Date().toISOString()
      };
      actions.addChatMessage(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearChat = () => {
    actions.clearChatHistory();
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const renderMessage = (message) => {
    const messageClass = `${styles.message} ${styles[`message${message.type.charAt(0).toUpperCase() + message.type.slice(1)}`]}`;
    
    return (
      <div key={message.id} className={messageClass}>
        <div className={styles.messageHeader}>
          <span className={styles.messageType}>
            {message.type === 'user' ? 'You' : 
             message.type === 'assistant' ? 'CGCM Assistant' : 'Error'}
          </span>
          <span className={styles.messageTime}>
            {formatTimestamp(message.timestamp)}
            {message.timeTaken && (
              <span className={styles.timeTaken}>
                • {message.timeTaken}s
              </span>
            )}
          </span>
        </div>
        <div className={styles.messageContent}>
          {typeof message.content === 'string' ? (
            <pre className={styles.messageText}>{message.content}</pre>
          ) : (
            <div className={styles.messageData}>
              {JSON.stringify(message.content, null, 2)}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!state.codebasePath) {
    return (
      <div className={styles.chatPage}>
        <div className="container">
          <div className={styles.errorState}>
            <AlertCircle size={48} />
            <h2>No Codebase Selected</h2>
            <p>Please go back and select a codebase path to start chatting.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.chatPage}>
      <div className="container">
        <div className={styles.chatHeader}>
          <div className={styles.headerInfo}>
            <MessageSquare className={styles.headerIcon} />
            <div>
              <h1 className={styles.chatTitle}>Context Assistant</h1>
              <p className={styles.codebasePath}>
                Codebase: <code>{state.codebasePath}</code>
              </p>
            </div>
          </div>
          
          <div className={styles.headerActions}>
            <div className={styles.statusIndicator}>
              {isPeriodicGatheringActive && (
                <div className={styles.activeStatus}>
                  <RefreshCw size={16} className={styles.rotateIcon} />
                  <span>Auto-sync active</span>
                </div>
              )}
            </div>
            
            {state.chatHistory.length > 0 && (
              <button 
                className="btn btn-secondary btn-sm"
                onClick={clearChat}
                title="Clear chat history"
              >
                Clear Chat
              </button>
            )}
          </div>
        </div>

        <div className={styles.chatContainer}>
          <div className={styles.chatMessages} ref={chatContainerRef}>
            {state.chatHistory.length === 0 ? (
              <div className={styles.welcomeMessage}>
                <MessageSquare size={64} className={styles.welcomeIcon} />
                <h3>Welcome to CGCM Assistant</h3>
                <p>
                  Ask questions about your codebase structure, functionality, or 
                  request specific context information. The system will use multiple 
                  retrieval tools to provide comprehensive answers.
                </p>
                <div className={styles.exampleQueries}>
                  <h4>Example queries:</h4>
                  <ul>
                    <li>"Show me the authentication flow in this codebase"</li>
                    <li>"What are the main API endpoints?"</li>
                    <li>"Explain the database schema structure"</li>
                    <li>"Find components related to user management"</li>
                  </ul>
                </div>
              </div>
            ) : (
              state.chatHistory.map(renderMessage)
            )}
            
            {isSubmitting && (
              <div className={`${styles.message} ${styles.messageLoading}`}>
                <div className={styles.messageHeader}>
                  <span className={styles.messageType}>CGCM Assistant</span>
                  <span className={styles.messageTime}>Processing...</span>
                </div>
                <div className={styles.messageContent}>
                  <div className={styles.loadingIndicator}>
                    <Loader size={20} className={styles.spinner} />
                    <span>Analyzing your query and gathering context...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className={styles.chatForm}>
            <div className={styles.inputContainer}>
              <textarea
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your codebase..."
                className={styles.queryInput}
                rows={1}
                disabled={isSubmitting}
              />
              <button
                type="submit"
                className={`btn btn-primary ${styles.sendButton}`}
                disabled={!query.trim() || isSubmitting}
                title="Send query"
              >
                {isSubmitting ? (
                  <Loader size={20} className={styles.spinner} />
                ) : (
                  <Send size={20} />
                )}
              </button>
            </div>
          </form>
        </div>

        {state.error && (
          <div className={styles.errorBanner}>
            <AlertCircle size={20} />
            <span>{state.error}</span>
            <button 
              onClick={() => actions.setError(null)}
              className={styles.errorClose}
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPage; 