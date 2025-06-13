import React, { createContext, useContext, useReducer, useEffect } from 'react';

// Initial state
const initialState = {
  theme: 'light',
  codebasePath: '',
  isContextGathered: false,
  isLoading: false,
  error: null,
  chatHistory: []
};

// Action types
export const ActionTypes = {
  SET_THEME: 'SET_THEME',
  SET_CODEBASE_PATH: 'SET_CODEBASE_PATH',
  SET_CONTEXT_GATHERED: 'SET_CONTEXT_GATHERED',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  ADD_CHAT_MESSAGE: 'ADD_CHAT_MESSAGE',
  CLEAR_CHAT_HISTORY: 'CLEAR_CHAT_HISTORY',
  RESET_STATE: 'RESET_STATE'
};

// Reducer function
const appReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_THEME:
      return { ...state, theme: action.payload };
    case ActionTypes.SET_CODEBASE_PATH:
      return { ...state, codebasePath: action.payload };
    case ActionTypes.SET_CONTEXT_GATHERED:
      return { ...state, isContextGathered: action.payload };
    case ActionTypes.SET_LOADING:
      return { ...state, isLoading: action.payload };
    case ActionTypes.SET_ERROR:
      return { ...state, error: action.payload };
    case ActionTypes.ADD_CHAT_MESSAGE:
      return { 
        ...state, 
        chatHistory: [...state.chatHistory, action.payload]
      };
    case ActionTypes.CLEAR_CHAT_HISTORY:
      return { ...state, chatHistory: [] };
    case ActionTypes.RESET_STATE:
      return { ...initialState, theme: state.theme };
    default:
      return state;
  }
};

// Create context
const AppContext = createContext();

// Context provider component
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Load theme from localStorage on component mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('cgcm-theme');
    if (savedTheme && ['light', 'dark'].includes(savedTheme)) {
      dispatch({ type: ActionTypes.SET_THEME, payload: savedTheme });
    }
  }, []);

  // Save theme to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('cgcm-theme', state.theme);
    // Update CSS custom property for theme
    document.documentElement.setAttribute('data-theme', state.theme);
  }, [state.theme]);

  // Action creators
  const actions = {
    setTheme: (theme) => dispatch({ type: ActionTypes.SET_THEME, payload: theme }),
    setCodebasePath: (path) => dispatch({ type: ActionTypes.SET_CODEBASE_PATH, payload: path }),
    setContextGathered: (gathered) => dispatch({ type: ActionTypes.SET_CONTEXT_GATHERED, payload: gathered }),
    setLoading: (loading) => dispatch({ type: ActionTypes.SET_LOADING, payload: loading }),
    setError: (error) => dispatch({ type: ActionTypes.SET_ERROR, payload: error }),
    addChatMessage: (message) => dispatch({ type: ActionTypes.ADD_CHAT_MESSAGE, payload: message }),
    clearChatHistory: () => dispatch({ type: ActionTypes.CLEAR_CHAT_HISTORY }),
    resetState: () => dispatch({ type: ActionTypes.RESET_STATE })
  };

  const value = {
    state,
    actions
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use the context
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext; 