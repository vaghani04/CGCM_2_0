import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Code, Database, Brain, Search, GitBranch, Zap } from 'lucide-react';
import styles from './LandingPage.module.css';

const LandingPage = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/setup');
  };

  const features = [
    {
      icon: <Database size={24} />,
      title: "Intelligent Context Storage",
      description: "Advanced chunking with MongoDB storage and Pinecone vector embeddings for efficient context retrieval."
    },
    {
      icon: <GitBranch size={24} />,
      title: "Repository Mapping",
      description: "Comprehensive codebase analysis stored in Neo4j graph database for structural understanding."
    },
    {
      icon: <Brain size={24} />,
      title: "AI-Powered Queries",
      description: "LLM-generated Cypher queries and intelligent context gathering based on user requirements."
    },
    {
      icon: <Search size={24} />,
      title: "Multi-Tool Retrieval",
      description: "RAG retrieval, repository mapping, and grep search tools for comprehensive context coverage."
    },
    {
      icon: <Zap size={24} />,
      title: "Real-time Updates",
      description: "Merkle tree-based change detection with automatic preprocessing and context updates."
    },
    {
      icon: <Code size={24} />,
      title: "Language Support",
      description: "Focused support for Python, JavaScript, and TypeScript codebases with framework awareness."
    }
  ];

  return (
    <div className={styles.landingPage}>
      <div className="container">
        {/* Hero Section */}
        <section className={styles.hero}>
          <div className={styles.heroContent}>
            <h1 className={styles.heroTitle}>
              Context Gathering <br />
              <span className={styles.titleAccent}>Management System</span>
            </h1>
            <p className={styles.heroDescription}>
              An intelligent context management system that analyzes and maintains deep contextual 
              understanding of large-scale codebases, designed for autonomous developer systems 
              and machine-to-machine collaboration.
            </p>
            <button 
              className={`btn btn-primary btn-lg ${styles.ctaButton}`}
              onClick={handleGetStarted}
            >
              Get Started
              <ArrowRight size={20} />
            </button>
          </div>
        </section>

        {/* Features Section */}
        <section className={styles.features}>
          <div className={styles.featuresHeader}>
            <h2 className={styles.sectionTitle}>System Capabilities</h2>
            <p className={styles.sectionDescription}>
              Built for analyzing repositories with 300+ files using advanced technologies 
              like FastAPI and Node.js frameworks.
            </p>
          </div>
          
          <div className={styles.featuresGrid}>
            {features.map((feature, index) => (
              <div key={index} className={`card ${styles.featureCard}`}>
                <div className={styles.featureIcon}>
                  {feature.icon}
                </div>
                <div className={styles.featureContent}>
                  <h3 className={styles.featureTitle}>{feature.title}</h3>
                  <p className={styles.featureDescription}>{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Architecture Overview */}
        <section className={styles.architecture}>
          <div className={styles.architectureHeader}>
            <h2 className={styles.sectionTitle}>System Architecture</h2>
            <p className={styles.sectionDescription}>
              A multi-layered approach to context management with intelligent preprocessing 
              and on-demand retrieval capabilities.
            </p>
          </div>
          
          <div className={styles.architectureFlow}>
            <div className={styles.flowStep}>
              <div className={styles.stepNumber}>1</div>
              <h4>Change Detection</h4>
              <p>Merkle tree-based monitoring detects codebase modifications</p>
            </div>
            
            <div className={styles.flowArrow}>→</div>
            
            <div className={styles.flowStep}>
              <div className={styles.stepNumber}>2</div>
              <h4>Context Processing</h4>
              <p>Chunking, embedding generation, and graph database updates</p>
            </div>
            
            <div className={styles.flowArrow}>→</div>
            
            <div className={styles.flowStep}>
              <div className={styles.stepNumber}>3</div>
              <h4>Query Processing</h4>
              <p>Multi-tool context retrieval and intelligent response generation</p>
            </div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className={styles.techStack}>
          <h2 className={styles.sectionTitle}>Technology Stack</h2>
          <div className={styles.techGrid}>
            <div className={styles.techCategory}>
              <h4>Storage & Retrieval</h4>
              <span className={styles.techList}>MongoDB • Pinecone • Neo4j</span>
            </div>
            <div className={styles.techCategory}>
              <h4>Processing</h4>
              <span className={styles.techList}>Chonkie • Voyage Embeddings • Merkle Trees</span>
            </div>
            <div className={styles.techCategory}>
              <h4>Frameworks</h4>
              <span className={styles.techList}>FastAPI • React • Node.js</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default LandingPage; 