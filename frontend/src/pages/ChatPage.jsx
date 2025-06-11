import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, AlertCircle, RefreshCw, MessageSquare, Copy, ChevronDown, ChevronRight } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { usePeriodicContextGather } from '../hooks/usePeriodicContextGather';
import contextService from '../services/contextService';
import styles from './ChatPage.module.css';

const ChatPage = () => {
  const { state, actions } = useApp();
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);
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

  // Clear copied status after 2 seconds
  useEffect(() => {
    if (copiedMessageId) {
      const timer = setTimeout(() => setCopiedMessageId(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [copiedMessageId]);

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
    
    // Reset textarea height after clearing
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

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

  // Auto-resize textarea
  const handleInputChange = (e) => {
    const textarea = e.target;
    setQuery(e.target.value);
    
    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';
    
    // Calculate the new height based on content
    const lineHeight = 24; // Approximate line height
    const maxLines = 4;
    const minHeight = lineHeight;
    const maxHeight = lineHeight * maxLines;
    
    const scrollHeight = textarea.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
    
    textarea.style.height = `${newHeight}px`;
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

  // Check if content is valid JSON
  const isValidJSON = (str) => {
    if (typeof str !== 'string') return false;
    try {
      const parsed = JSON.parse(str);
      return typeof parsed === 'object' && parsed !== null;
    } catch {
      return false;
    }
  };

  // Copy to clipboard functionality
  const copyToClipboard = async (content, messageId) => {
    try {
      const textToCopy = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
      await navigator.clipboard.writeText(textToCopy);
      setCopiedMessageId(messageId);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // JSON syntax highlighting component
  const JSONHighlighter = ({ data, isRoot = true }) => {
    const [collapsed, setCollapsed] = useState({});
    
    const toggleCollapse = (path) => {
      setCollapsed(prev => ({
        ...prev,
        [path]: !prev[path]
      }));
    };

    const renderValue = (value, key, path = '') => {
      const currentPath = path ? `${path}.${key}` : key;
      
      if (value === null) {
        return <span className={styles.jsonNull}>null</span>;
      }
      
      if (typeof value === 'boolean') {
        return <span className={styles.jsonBoolean}>{value.toString()}</span>;
      }
      
      if (typeof value === 'number') {
        return <span className={styles.jsonNumber}>{value}</span>;
      }
      
      if (typeof value === 'string') {
        return <span className={styles.jsonString}>"{value}"</span>;
      }
      
      if (Array.isArray(value)) {
        const isCollapsed = collapsed[currentPath];
        return (
          <div className={styles.jsonArray}>
            <button 
              className={styles.jsonToggle}
              onClick={() => toggleCollapse(currentPath)}
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
              <span className={styles.jsonBracket}>[</span>
              {isCollapsed && <span className={styles.jsonEllipsis}>...{value.length} items</span>}
            </button>
            {!isCollapsed && (
              <div className={styles.jsonContent}>
                {value.map((item, index) => (
                  <div key={index} className={styles.jsonItem}>
                    <span className={styles.jsonIndex}>{index}:</span>
                    {renderValue(item, index, currentPath)}
                    {index < value.length - 1 && <span className={styles.jsonComma}>,</span>}
                  </div>
                ))}
              </div>
            )}
            {!isCollapsed && <span className={styles.jsonBracket}>]</span>}
          </div>
        );
      }
      
      if (typeof value === 'object') {
        const keys = Object.keys(value);
        const isCollapsed = collapsed[currentPath];
        return (
          <div className={styles.jsonObject}>
            <button 
              className={styles.jsonToggle}
              onClick={() => toggleCollapse(currentPath)}
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
              <span className={styles.jsonBracket}>{"{"}</span>
              {isCollapsed && <span className={styles.jsonEllipsis}>...{keys.length} keys</span>}
            </button>
            {!isCollapsed && (
              <div className={styles.jsonContent}>
                {keys.map((objKey, index) => (
                  <div key={objKey} className={styles.jsonItem}>
                    <span className={styles.jsonKey}>"{objKey}":</span>
                    {renderValue(value[objKey], objKey, currentPath)}
                    {index < keys.length - 1 && <span className={styles.jsonComma}>,</span>}
                  </div>
                ))}
              </div>
            )}
            {!isCollapsed && <span className={styles.jsonBracket}>{"}"}</span>}
          </div>
        );
      }
      
      return <span>{String(value)}</span>;
    };

    return (
      <div className={styles.jsonHighlighter}>
        {renderValue(data, 'root')}
      </div>
    );
  };

  const renderMessage = (message) => {
    const messageClass = `${styles.message} ${styles[`message${message.type.charAt(0).toUpperCase() + message.type.slice(1)}`]}`;
    
    // Determine if content should be displayed as JSON
    let isJSONContent = false;
    let parsedContent = null;
    
    if (typeof message.content === 'string') {
      isJSONContent = isValidJSON(message.content);
      if (isJSONContent) {
        try {
          parsedContent = JSON.parse(message.content);
        } catch {
          isJSONContent = false;
        }
      }
    } else if (typeof message.content === 'object') {
      isJSONContent = true;
      parsedContent = message.content;
    }
    
    return (
      <div key={message.id} className={messageClass}>
        <div className={styles.messageHeader}>
          <span className={styles.messageType}>
            {message.type === 'user' ? 'You' : 
             message.type === 'assistant' ? 'CGCM Assistant' : 'Error'}
          </span>
          <div className={styles.messageActions}>
            <span className={styles.messageTime}>
              {formatTimestamp(message.timestamp)}
              {message.timeTaken && (
                <span className={styles.timeTaken}>
                  • {message.timeTaken}s
                </span>
              )}
            </span>
            <button
              className={styles.copyButton}
              onClick={() => copyToClipboard(message.content, message.id)}
              title="Copy to clipboard"
            >
              <Copy size={16} />
              {copiedMessageId === message.id && (
                <span className={styles.copiedText}>Copied!</span>
              )}
            </button>
          </div>
        </div>
        <div className={styles.messageContent}>
          {isJSONContent ? (
            <div className={styles.jsonResponse}>
              <div className={styles.jsonHeader}>
                <span className={styles.jsonLabel}>JSON Response</span>
              </div>
              <JSONHighlighter data={parsedContent} />
            </div>
          ) : (
            <pre className={styles.messageText}>{message.content}</pre>
          )}
        </div>
      </div>
    );
  };

  if (!state.codebasePath) {
    return (
      <div className={styles.chatPage}>
        <div className={styles.chatPageContainer}>
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
      <div className={styles.chatPageContainer}>
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
                onChange={handleInputChange}
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