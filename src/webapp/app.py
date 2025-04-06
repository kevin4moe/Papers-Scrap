# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import pandas as pd
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import json

app = Flask(__name__, static_folder='static')

# Load the dataset
# In a production environment, you would properly handle the data loading
# and ensure the dataset is available
def load_dataset():
    # For demonstration purposes
    # In a real implementation, you would load your actual dataset here
    try:
        # Try to load from a local CSV file if available
        if os.path.exists('papers.csv'):
            return pd.read_csv('papers.csv')
        else:
            # Create a sample dataset for demonstration
            sample_data = {
                'clean_title': [
                    "Air pollutants, economic growth and public health",
                    "The impact of climate change on economic development",
                    "Machine learning algorithms for medical diagnosis",
                    "Neural networks and deep learning applications",
                    "Environmental factors affecting renewable energy adoption",
                    "A review of sustainable development goals and policy implications",
                    "Natural language processing techniques for scientific literature",
                    "The effects of globalization on local economies",
                    "Advancements in quantum computing: A comprehensive survey",
                    "Blockchain technology applications in supply chain management"
                ],
                'description': [
                    "This paper examines the relationship between air pollution, economic growth, and public health outcomes in developing countries.",
                    "A comprehensive analysis of how climate change affects economic development pathways and potential mitigation strategies.",
                    "This study reviews current machine learning approaches for medical diagnosis and their effectiveness compared to traditional methods.",
                    "An overview of neural network architectures and their applications in various domains.",
                    "Analysis of environmental and policy factors that influence the adoption of renewable energy technologies.",
                    "This paper reviews progress towards sustainable development goals and suggests policy frameworks for implementation.",
                    "A survey of NLP techniques specifically designed for processing and analyzing scientific literature.",
                    "This research examines how globalization trends impact local economic structures and labor markets.",
                    "Comprehensive review of recent advancements in quantum computing research and potential applications.",
                    "This paper explores how blockchain technology can improve transparency and efficiency in supply chain management."
                ],
                'citations': [156, 203, 89, 245, 120, 78, 134, 167, 92, 114],
                'year': [2019, 2020, 2021, 2022, 2020, 2021, 2022, 2019, 2022, 2021],
                'authors': [
                    "Johnson et al.",
                    "Chen, Williams, and Garcia",
                    "Patel and Smith",
                    "Kim, Lee, and Park",
                    "Rodriguez et al.",
                    "Thompson and Brown",
                    "Nguyen, Wilson, and Das",
                    "Clark and Martin",
                    "Singh, Cohen, and White",
                    "Ahmed and Wilson"
                ],
                'url': [
                    "https://example.org/paper1",
                    "https://example.org/paper2",
                    "https://example.org/paper3",
                    "https://example.org/paper4",
                    "https://example.org/paper5",
                    "https://example.org/paper6",
                    "https://example.org/paper7",
                    "https://example.org/paper8",
                    "https://example.org/paper9",
                    "https://example.org/paper10"
                ]
            }
            return pd.DataFrame(sample_data)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        # Return a minimal dataset if there's an error
        return pd.DataFrame({
            'clean_title': ["Sample paper"],
            'description': ["Sample description"],
            'citations': [0]
        })

# Global variables for the TF-IDF model and FAISS index
df = load_dataset()
tfidf_vectorizer = None
tfidf_matrix = None
faiss_index = None

def initialize_search_engine():
    global tfidf_vectorizer, tfidf_matrix, faiss_index
    
    # Combine title and description for each paper
    corpus = [str(row['clean_title']) + " " + str(row['description']) for _, row in df.iterrows()]
    
    # Create and fit TF-IDF vectorizer
    tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=1024)
    tfidf_matrix = tfidf_vectorizer.fit_transform(corpus)
    
    # Create FAISS index
    faiss_index = faiss.IndexFlatIP(tfidf_matrix.shape[1])
    
    # Convert sparse matrix to dense and normalize
    vectors = tfidf_matrix.toarray().astype('float32')
    faiss.normalize_L2(vectors)
    faiss_index.add(vectors)

# Initialize the search engine when the app starts
initialize_search_engine()

def recommend_papers(query_title, query_description, top_k=5):
    global tfidf_vectorizer, faiss_index, df
    
    # Combine query title and description
    query_text = str(query_title) + " " + str(query_description)
   
    # Transform the query using the same vectorizer
    query_vector = tfidf_vectorizer.transform([query_text])
   
    # Convert to dense array and normalize
    query_vector_dense = query_vector.toarray().astype('float32')
    faiss.normalize_L2(query_vector_dense)
   
    # Search the index
    distances, indices = faiss_index.search(query_vector_dense, top_k)
    
    # Prepare results
    results = []
    for i, idx in enumerate(indices[0]):
        paper = df.iloc[idx]
        paper_dict = {
            'title': paper['clean_title'],
            'description': str(paper['description'])[:200] + "..." if pd.notna(paper['description']) and len(str(paper['description'])) > 200 else str(paper['description']) if pd.notna(paper['description']) else "No description available",
            'citations': int(paper['citations']) if 'citations' in paper and pd.notna(paper['citations']) else None,
            'relevance_score': float(distances[0][i]),
        }
        
        # Add optional fields if they exist
        if 'year' in paper and pd.notna(paper['year']):
            paper_dict['year'] = int(paper['year'])
        if 'authors' in paper and pd.notna(paper['authors']):
            paper_dict['authors'] = str(paper['authors'])
        if 'url' in paper and pd.notna(paper['url']):
            paper_dict['url'] = str(paper['url'])
            
        results.append(paper_dict)
    
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.json
        query_title = data.get('queryTitle', '')
        query_description = data.get('queryDescription', '')
        top_k = min(int(data.get('topK', 5)), 20)  # Limit to max 20 results
        
        results = recommend_papers(query_title, query_description, top_k)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        print(f"Error during search: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Serve static files (HTML, CSS, JS)
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Save the HTML file to the templates directory
def setup_templates():
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w') as f:
        # This would be the HTML content from your landing page
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Academic Paper Search Engine</title>
    <style>
        :root {
            --primary-color: #4a6fa5;
            --secondary-color: #334e68;
            --accent-color: #63b3ed;
            --bg-color: #f8fafc;
            --text-color: #2d3748;
            --card-bg: #ffffff;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background-color: var(--primary-color);
            color: white;
            padding: 20px 0;
            text-align: center;
            box-shadow: var(--shadow);
        }
        
        h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        
        .search-box {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 8px;
            box-shadow: var(--shadow);
            margin: 30px 0;
        }
        
        .search-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }
        
        label {
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        input, textarea {
            padding: 12px;
            border: 1px solid #cbd5e0;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        button {
            background-color: var(--accent-color);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        button:hover {
            background-color: #4299e1;
        }
        
        .results {
            margin-top: 30px;
        }
        
        .paper-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: var(--shadow);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .paper-title {
            color: var(--primary-color);
            margin-top: 0;
        }
        
        .paper-meta {
            display: flex;
            gap: 20px;
            color: #718096;
            margin-bottom: 10px;
        }
        
        .paper-description {
            margin-bottom: 10px;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top: 4px solid var(--accent-color);
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error-message {
            color: #e53e3e;
            background-color: #fed7d7;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: none;
        }
        
        footer {
            text-align: center;
            padding: 20px;
            margin-top: 50px;
            background-color: var(--secondary-color);
            color: white;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Academic Paper Search Engine</h1>
            <p>Find relevant academic papers based on your research interests</p>
        </div>
    </header>
    
    <main class="container">
        <div class="search-box">
            <h2>Search for Papers</h2>
            <form id="searchForm" class="search-form">
                <div class="form-group">
                    <label for="queryTitle">Paper Title or Keywords</label>
                    <input type="text" id="queryTitle" name="queryTitle" placeholder="Enter main topic or keywords" required>
                </div>
                
                <div class="form-group">
                    <label for="queryDescription">Additional Description (Optional)</label>
                    <textarea id="queryDescription" name="queryDescription" rows="4" placeholder="Enter more details about what you're looking for"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="topK">Number of Results</label>
                    <input type="number" id="topK" name="topK" min="1" max="20" value="5">
                </div>
                
                <button type="submit" id="searchButton">Search Papers</button>
            </form>
        </div>
        
        <div id="errorMessage" class="error-message"></div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Searching academic papers...</p>
        </div>
        
        <div id="results" class="results"></div>
    </main>
    
    <footer>
        <div class="container">
            <p>Academic Paper Search Engine - Proof of Concept</p>
        </div>
    </footer>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const searchForm = document.getElementById('searchForm');
            const resultsContainer = document.getElementById('results');
            const loadingIndicator = document.getElementById('loading');
            const errorMessage = document.getElementById('errorMessage');
            
            searchForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                // Clear previous results
                resultsContainer.innerHTML = '';
                errorMessage.style.display = 'none';
                
                // Show loading indicator
                loadingIndicator.style.display = 'block';
                
                // Get form data
                const formData = {
                    queryTitle: document.getElementById('queryTitle').value,
                    queryDescription: document.getElementById('queryDescription').value,
                    topK: parseInt(document.getElementById('topK').value)
                };
                
                try {
                    // Make API request
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });
                    
                    if (!response.ok) {
                        throw new Error('Error searching papers');
                    }
                    
                    const data = await response.json();
                    
                    // Hide loading indicator
                    loadingIndicator.style.display = 'none';
                    
                    // Display results
                    if (data.results && data.results.length > 0) {
                        const resultsHTML = data.results.map((paper, index) => `
                            <div class="paper-card">
                                <h3 class="paper-title">${index + 1}. ${paper.title}</h3>
                                <div class="paper-meta">
                                    <span>Citations: ${paper.citations || 'N/A'}</span>
                                    ${paper.year ? `<span>Year: ${paper.year}</span>` : ''}
                                    ${paper.authors ? `<span>Authors: ${paper.authors}</span>` : ''}
                                </div>
                                <p class="paper-description">${paper.description || 'No description available'}</p>
                                ${paper.url ? `<a href="${paper.url}" target="_blank">View Paper</a>` : ''}
                            </div>
                        `).join('');
                        
                        resultsContainer.innerHTML = `
                            <h2>Search Results</h2>
                            <p>Found ${data.results.length} papers for "${formData.queryTitle}"</p>
                            ${resultsHTML}
                        `;
                    } else {
                        resultsContainer.innerHTML = `
                            <h2>No Results Found</h2>
                            <p>No papers matched your search criteria. Try different keywords.</p>
                        `;
                    }
                } catch (error) {
                    // Hide loading indicator
                    loadingIndicator.style.display = 'none';
                    
                    // Show error message
                    errorMessage.textContent = 'An error occurred while searching. Please try again.';
                    errorMessage.style.display = 'block';
                    console.error('Search error:', error);
                }
            });
        });
    </script>
</body>
</html>""")

if __name__ == '__main__':
    # Setup template directory and files
    setup_templates()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)