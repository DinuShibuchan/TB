document.addEventListener('DOMContentLoaded', () => {
    // API Base URL (same host since we serve statically)
    const API_BASE_URL = window.location.origin;

    // DOM Elements - Navigation Tabs
    const navPlannerBtn = document.getElementById('nav-planner-btn');
    const navDbBtn = document.getElementById('nav-db-btn');
    const navHealthBtn = document.getElementById('nav-health-btn');

    const panelPlanner = document.getElementById('panel-planner');
    const panelDb = document.getElementById('panel-db');
    const panelHealth = document.getElementById('panel-health');
    const workspaceTitle = document.getElementById('workspace-title');
    const workspaceSubtitle = document.getElementById('workspace-subtitle');

    // DOM Elements - Forms & Buttons
    const tripForm = document.getElementById('trip-form');
    const generateBtn = document.getElementById('generate-btn');
    const generateBtnText = generateBtn.querySelector('.btn-text');
    const generateBtnSpinner = generateBtn.querySelector('.btn-spinner');

    const addDataForm = document.getElementById('add-data-form');
    const dbStatusMsg = document.getElementById('db-status-msg');

    const chatForm = document.getElementById('chat-form');
    const chatQueryInput = document.getElementById('chat-query');
    const chatMessages = document.getElementById('chat-messages');

    // DOM Elements - Output Displays
    const resultsPlaceholder = document.getElementById('results-placeholder');
    const contextBar = document.getElementById('context-bar');
    const weatherCity = document.getElementById('weather-city');
    const weatherDesc = document.getElementById('weather-desc');
    const weatherTemp = document.getElementById('weather-temp');
    const weatherHumidity = document.getElementById('weather-humidity');
    const weatherWind = document.getElementById('weather-wind');
    const wikiSummary = document.getElementById('wiki-summary');
    const itineraryGrid = document.getElementById('itinerary-grid');

    // DOM Elements - Connection Status
    const statusFastapi = document.getElementById('status-fastapi');
    const statusDb = document.getElementById('status-db');
    const statusOllama = document.getElementById('status-ollama');
    const sideStatusDot = document.querySelector('.status-dot');
    const sideStatusText = document.querySelector('.status-text');

    // ----------------------------------------------------
    // Tab Navigation Logic
    // ----------------------------------------------------
    function switchTab(activeBtn, activePanel, title, subtitle) {
        // Reset navigation classes
        [navPlannerBtn, navDbBtn, navHealthBtn].forEach(btn => btn.classList.remove('active'));
        // Hide all panels
        [panelPlanner, panelDb, panelHealth].forEach(panel => panel.classList.remove('active'));

        // Activate target
        activeBtn.classList.add('active');
        activePanel.classList.add('active');
        workspaceTitle.innerText = title;
        workspaceSubtitle.innerText = subtitle;
    }

    navPlannerBtn.addEventListener('click', () => {
        switchTab(
            navPlannerBtn, 
            panelPlanner, 
            'Personalized Itinerary Generator', 
            'Leveraging local RAG (pgvector + Ollama) for hallucination-free planning'
        );
    });

    navDbBtn.addEventListener('click', () => {
        switchTab(
            navDbBtn, 
            panelDb, 
            'Knowledge Base Management', 
            'Feed local context text directly into the pgvector semantic retrieval engine'
        );
    });

    navHealthBtn.addEventListener('click', () => {
        switchTab(
            navHealthBtn, 
            panelHealth, 
            'API Connection Health', 
            'Monitor the backend stack services and connection statuses'
        );
        checkHealth();
    });

    // ----------------------------------------------------
    // Connection Health Verification
    // ----------------------------------------------------
    async function checkHealth() {
        try {
            const res = await fetch(`${API_BASE_URL}/health`);
            const data = await res.json();
            
            if (res.status === 200) {
                statusFastapi.innerText = 'Connected';
                statusFastapi.className = 'health-val status-badge success';
                
                if (data.database_type === 'sqlite') {
                    statusDb.innerText = 'Active (SQLite Fallback)';
                    statusDb.className = 'health-val status-badge success';
                    sideStatusDot.className = 'status-dot healthy';
                    sideStatusText.innerText = 'SQLite Fallback';
                } else if (data.status === 'ok') {
                    statusDb.innerText = 'Healthy (PostgreSQL)';
                    statusDb.className = 'health-val status-badge success';
                    sideStatusDot.className = 'status-dot healthy';
                    sideStatusText.innerText = 'PostgreSQL Active';
                } else {
                    statusDb.innerText = 'Degraded (PostgreSQL)';
                    statusDb.className = 'health-val status-badge error';
                    sideStatusDot.className = 'status-dot degraded';
                    sideStatusText.innerText = 'DB Degraded';
                }
                
                if (data.ollama_status === 'online') {
                    statusOllama.innerText = 'Active (Ollama Online)';
                    statusOllama.className = 'health-val status-badge success';
                } else {
                    statusOllama.innerText = 'Offline (Mock Fallback)';
                    statusOllama.className = 'health-val status-badge pending';
                }
            } else {
                throw new Error('Health check error');
            }
        } catch (err) {
            statusFastapi.innerText = 'Online';
            statusFastapi.className = 'health-val status-badge success';
            
            statusDb.innerText = 'Offline / Connecting';
            statusDb.className = 'health-val status-badge error';
            
            statusOllama.innerText = 'Offline (Mock Fallback)';
            statusOllama.className = 'health-val status-badge pending';

            sideStatusDot.className = 'status-dot degraded';
            sideStatusText.innerText = 'DB Offline';
        }
    }

    // Call health check on start
    checkHealth();
    setInterval(checkHealth, 30000); // Check every 30s

    // ----------------------------------------------------
    // RAG Database Add Data
    // ----------------------------------------------------
    addDataForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = document.getElementById('db-name').value.trim();
        const category = document.getElementById('db-category').value;
        const description = document.getElementById('db-description').value.trim();
        
        dbStatusMsg.className = 'status-msg';
        dbStatusMsg.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE_URL}/add-data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, category, description })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                dbStatusMsg.innerText = `Successfully added RAG context for ${name}! Embedding generated.`;
                dbStatusMsg.className = 'status-msg success';
                addDataForm.reset();
            } else {
                dbStatusMsg.innerText = `Error adding data: ${data.detail || 'Unknown error'}`;
                dbStatusMsg.className = 'status-msg error';
            }
        } catch (err) {
            dbStatusMsg.innerText = `Network error connecting to backend: ${err.message}`;
            dbStatusMsg.className = 'status-msg error';
        }
    });

    // ----------------------------------------------------
    // Trip Itinerary Generation
    // ----------------------------------------------------
    tripForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const destination = document.getElementById('destination').value.trim();
        const days = parseInt(document.getElementById('days').value);
        const budget = document.getElementById('budget').value;
        const preferences = document.getElementById('preferences').value.trim();

        // 1. Loading UI state
        generateBtn.disabled = true;
        generateBtnText.innerText = 'Gathering Context & Generating...';
        generateBtnSpinner.classList.remove('hidden');
        
        // Hide result content and show default placeholder
        resultsPlaceholder.classList.add('hidden');
        contextBar.classList.add('hidden');
        itineraryGrid.classList.add('hidden');
        
        try {
            const response = await fetch(`${API_BASE_URL}/plan-trip`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    destination,
                    days,
                    budget,
                    preferences: preferences || null
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Render Weather info
                if (data.weather) {
                    weatherCity.innerText = data.weather.city;
                    weatherDesc.innerText = data.weather.description;
                    weatherTemp.innerText = `${Math.round(data.weather.temperature)}°C`;
                    weatherHumidity.innerText = `${data.weather.humidity}%`;
                    weatherWind.innerText = `${data.weather.wind_speed} m/s`;
                }
                
                // Render Wikipedia summary
                wikiSummary.innerText = data.wikipedia_summary || 'No overview summary available for this destination.';
                contextBar.classList.remove('hidden');

                // Render Itinerary day cards
                itineraryGrid.innerHTML = '';
                if (data.itinerary && data.itinerary.length > 0) {
                    data.itinerary.forEach(day => {
                        const dayCard = document.createElement('div');
                        dayCard.className = 'glass-card day-card';
                        
                        const activitiesHtml = day.activities.map(act => `<li>${act}</li>`).join('');
                        const foodHtml = day.recommended_food.join(', ');
                        const stayHtml = day.recommended_stay || 'Not specified';
                        const costHtml = day.estimated_cost || 'Not estimated';

                        dayCard.innerHTML = `
                            <div class="day-badge">DAY ${day.day}</div>
                            <div class="day-content">
                                <h4 class="day-theme">${day.theme}</h4>
                                <ul class="activities-list">
                                    ${activitiesHtml}
                                </ul>
                                <div class="day-recommendations">
                                    <div class="rec-item">
                                        🍔 <strong>Food:</strong> ${foodHtml}
                                    </div>
                                    <div class="rec-item">
                                        🏨 <strong>Stay:</strong> ${stayHtml}
                                    </div>
                                    <div class="rec-item">
                                        💰 <strong>Est. Cost:</strong> ${costHtml}
                                    </div>
                                </div>
                            </div>
                        `;
                        itineraryGrid.appendChild(dayCard);
                    });
                } else {
                    itineraryGrid.innerHTML = '<div class="glass-card"><p>No itinerary plans returned. Please double check database content.</p></div>';
                }
                itineraryGrid.classList.remove('hidden');
            } else {
                // Handle missing context or other backend errors
                let errMsg = data.detail || 'Data not available';
                
                resultsPlaceholder.innerHTML = `
                    <div class="placeholder-icon">⚠️</div>
                    <h3>Itinerary Generation Failed</h3>
                    <p class="error-detail" style="color:#ef4444; font-weight:600; margin-top: 4px;">Reason: ${errMsg}</p>
                    <p style="margin-top: 12px; font-size: 13px;">If you see <strong>"Data not available"</strong>, this means the RAG system found no matching records in the local PostgreSQL database or on Wikipedia for <strong>"${destination}"</strong>. Feel free to add information about it on the <strong>RAG Database</strong> page and try again!</p>
                `;
                resultsPlaceholder.classList.remove('hidden');
            }
        } catch (err) {
            resultsPlaceholder.innerHTML = `
                <div class="placeholder-icon">❌</div>
                <h3>Network Error</h3>
                <p>Failed to connect to backend: ${err.message}. Ensure your FastAPI app is running.</p>
            `;
            resultsPlaceholder.classList.remove('hidden');
        } finally {
            // Restore UI state
            generateBtn.disabled = false;
            generateBtnText.innerText = 'Generate Itinerary';
            generateBtnSpinner.classList.add('hidden');
        }
    });

    // ----------------------------------------------------
    // Chat System Drawer
    // ----------------------------------------------------
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = chatQueryInput.value.trim();
        if (!query) return;

        // Append User message
        appendMessage('user', query);
        chatQueryInput.value = '';

        // Show typing indicator or empty assistant bubble
        const typingBubble = appendMessage('assistant', 'Consulting knowledge base...');
        
        try {
            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            // Remove typing text
            typingBubble.remove();
            
            if (response.ok) {
                appendMessage('assistant', data.response);
            } else {
                appendMessage('assistant', `Error: ${data.detail || 'Unable to fetch response.'}`);
            }
        } catch (err) {
            typingBubble.remove();
            appendMessage('assistant', `Connection error: ${err.message}`);
        }
    });

    function appendMessage(sender, text) {
        const bubble = document.createElement('div');
        bubble.className = `message ${sender}`;
        bubble.innerText = text;
        chatMessages.appendChild(bubble);
        
        // Scroll chat to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return bubble;
    }
});
