# CGCM 2.0 Frontend

A modern React frontend for the Context Gathering Management System (CGCM 2.0), providing an intuitive interface for codebase context analysis and AI-powered query processing.

## 🚀 Features

- **Modern React Architecture**: Built with React 19, React Router, and modular component structure
- **Dark/Light Theme Support**: Seamless theme switching with persistent preferences
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Real-time Processing**: Live status updates during context gathering
- **Chat Interface**: Interactive query system with comprehensive response display
- **Periodic Updates**: Automatic background context synchronization
- **Error Handling**: Comprehensive error states and user feedback

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   └── layout/          # Layout components (Header, etc.)
│   ├── pages/               # Page components
│   │   ├── LandingPage.jsx  # System overview and introduction
│   │   ├── SetupPage.jsx    # Codebase configuration
│   │   └── ChatPage.jsx     # Query interface
│   ├── context/             # React Context providers
│   │   └── AppContext.jsx   # Global state management
│   ├── hooks/               # Custom React hooks
│   │   └── usePeriodicContextGather.js
│   ├── services/            # API communication
│   │   └── contextService.js
│   ├── utils/               # Utility functions
│   ├── styles/              # Global styling
│   │   └── globals.css      # Theme variables and base styles
│   └── config/              # Configuration files
│       └── api.js           # API client setup
├── scripts/                 # Standalone scripts
│   └── periodic-context-gather.js
└── public/                  # Static assets
```

## 🛠️ Installation

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   ```

2. **Configure Environment** (Optional)
   ```bash
   # Create .env file for custom API URL
   echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env
   ```

3. **Start Development Server**
   ```bash
   npm run dev
   ```

   The application will be available at `http://localhost:5173`

## 🎯 Usage Flow

### 1. Landing Page
- System overview and capability showcase
- Technology stack information
- Architecture flow visualization
- "Get Started" button to begin setup

### 2. Setup Page
- **Codebase Path Input**: Enter the path to your codebase
- **Processing Status**: Real-time feedback during context gathering
- **Processing Steps**: Visual indication of current processing stage
- **Auto-redirect**: Automatic navigation to chat interface upon completion

### 3. Chat Interface
- **Query Input**: Natural language questions about your codebase
- **Response Display**: Formatted responses with timing information
- **Auto-sync Status**: Visual indicator of periodic context updates
- **Chat History**: Persistent conversation thread
- **Error Handling**: Clear error messages and recovery options

## 🔧 Configuration

### API Configuration
Update `src/config/api.js` to modify:
- Base URL for backend API
- Request timeout settings
- Default headers

### Theme Configuration
Modify `src/styles/globals.css` to customize:
- Color schemes for light/dark themes
- Typography settings
- Spacing and layout variables
- Animation preferences

### Periodic Updates
Adjust `src/hooks/usePeriodicContextGather.js` to change:
- Update interval (default: 3 minutes)
- Error handling behavior
- Logging preferences

## 📜 Scripts

### Development Scripts
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint
```

### Standalone Scripts
```bash
# Run periodic context gathering independently
node scripts/periodic-context-gather.js /path/to/codebase

# Run with custom interval (5 minutes)
node scripts/periodic-context-gather.js /path/to/codebase 5

# Run with custom API URL
REACT_APP_API_URL=http://localhost:3001/api/v1 node scripts/periodic-context-gather.js /path/to/codebase

# Get help
node scripts/periodic-context-gather.js --help
```

## 🎨 Theming

The application supports both light and dark themes with automatic persistence. Theme switching is available via the header toggle button.

### Custom Theme Creation
1. Add new theme variables in `src/styles/globals.css`
2. Update theme switching logic in `src/context/AppContext.jsx`
3. Test across all components for consistency

## 📱 Responsive Design

The interface is optimized for various screen sizes:
- **Desktop**: Full feature set with optimal spacing
- **Tablet**: Adapted layouts with touch-friendly interactions
- **Mobile**: Streamlined interface with essential features

## 🔍 API Integration

### Context Service
The `contextService` handles all backend communication:

```javascript
// Trigger context gathering
await contextService.gatherContext(codebasePath);

// Submit user query
await contextService.submitUserQuery(query, codebasePath);
```

### Error Handling
- Network errors with retry suggestions
- API errors with detailed messages
- Timeout handling for long operations
- Graceful degradation for offline scenarios

## 🚨 Troubleshooting

### Common Issues

1. **Dependency Conflicts**
   ```bash
   npm install --legacy-peer-deps
   ```

2. **API Connection Issues**
   - Verify backend server is running
   - Check API URL configuration
   - Review network connectivity

3. **Theme Not Persisting**
   - Clear browser localStorage
   - Check browser storage permissions

4. **Build Errors**
   ```bash
   npm run lint
   npm run build
   ```

### Performance Optimization
- Enable React DevTools for component profiling
- Monitor network requests in browser DevTools
- Use React.memo for expensive components
- Implement virtual scrolling for large chat histories

## 🔮 Future Enhancements

- **File Upload**: Direct codebase upload interface
- **Advanced Filtering**: Query history search and filtering
- **Export Options**: Save conversations and context data
- **Real-time Collaboration**: Multi-user chat sessions
- **Analytics Dashboard**: Usage statistics and insights
- **Plugin System**: Extensible functionality framework

## 📄 License

This project is part of the CGCM 2.0 system. See the main project license for details.

## 🤝 Contributing

1. Follow existing code style and patterns
2. Add appropriate tests for new features
3. Update documentation for API changes
4. Ensure responsive design compatibility
5. Test theme switching functionality
