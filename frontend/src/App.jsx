import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import Header from './components/layout/Header';
import LandingPage from './pages/LandingPage';
import SetupPage from './pages/SetupPage';
import ChatPage from './pages/ChatPage';
import './styles/globals.css';

function App() {
  return (
    <AppProvider>
      <Router>
        <div className="app">
          <Header />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/setup" element={<SetupPage />} />
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AppProvider>
  );
}

export default App;
