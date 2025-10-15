/**
 * Modular Relay Dashboard JavaScript
 * Advanced client-side functionality for the dashboard
 */

class ModularRelayDashboard {
    constructor() {
        this.config = {
            apiBaseUrl: '',
            refreshInterval: 300000, // 5 minutes
            chartColors: {
                primary: '#004c91',
                secondary: '#0071ce',
                accent: '#ffc220',
                success: '#28a745',
                warning: '#ffc107',
                danger: '#dc3545',
                info: '#17a2b8'
            },
            animations: {
                duration: 500,
                easing: 'ease-in-out'
            }
        };

        this.cache = new Map();
        this.eventListeners = new Map();
        this.chartInstances = new Map();
        this.refreshTimer = null;
        this.isLoading = false;

        this.init();
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        console.log('🚀 Initializing Modular Relay Dashboard...');
        
        try {
            this.setupEventListeners();
            this.initializeChartDefaults();
            await this.loadInitialData();
            this.startAutoRefresh();
            this.setupKeyboardShortcuts();
            this.setupIntersectionObserver();
            
            console.log('✅ Dashboard initialized successfully');
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.showNotification('Dashboard initialization failed', 'error');
        }
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Refresh button
        this.addEventListener('refresh-data', 'click', () => this.refreshAllData());

        // Tab navigation
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            this.addEventListener(tab, 'shown.bs.tab', (event) => {
                const targetTab = event.target.getAttribute('data-bs-target').replace('#', '');
                this.handleTabChange(targetTab);
            });
        });

        // Window resize handler for responsive charts
        this.addEventListener(window, 'resize', 
            this.debounce(() => this.handleWindowResize(), 300)
        );

        // Page visibility change
        this.addEventListener(document, 'visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.handlePageVisible();
            } else {
                this.handlePageHidden();
            }
        });

        // Network status
        this.addEventListener(window, 'online', () => this.handleNetworkOnline());
        this.addEventListener(window, 'offline', () => this.handleNetworkOffline());

        // Keyboard shortcuts
        this.addEventListener(document, 'keydown', (e) => this.handleKeyboardShortcuts(e));

        // Chart interaction events
        this.setupChartEventListeners();
    }

    /**
     * Add event listener with cleanup tracking
     */
    addEventListener(element, event, handler) {
        const target = typeof element === 'string' ? document.getElementById(element) : element;
        if (!target) return;

        target.addEventListener(event, handler);
        
        // Track for cleanup
        const key = `${target.id || 'window'}-${event}`;
        if (!this.eventListeners.has(key)) {
            this.eventListeners.set(key, []);
        }
        this.eventListeners.get(key).push({ target, event, handler });
    }

    /**
     * Initialize Plotly chart defaults
     */
    initializeChartDefaults() {
        // Set global Plotly configuration
        Plotly.setPlotConfig({
            displayModeBar: 'hover',
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            responsive: true
        });

        // Default layout template
        this.defaultLayout = {
            font: {
                family: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
                size: 12,
                color: '#212529'
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 40, r: 20, b: 40, l: 60 },
            showlegend: true,
            legend: {
                orientation: 'h',
                y: -0.2,
                x: 0.5,
                xanchor: 'center'
            },
            colorway: Object.values(this.config.chartColors)
        };
    }

    /**
     * Load initial dashboard data
     */
    async loadInitialData() {
        this.setLoadingState(true);
        
        try {
            // Load data in parallel for better performance
            const [executiveData, costData] = await Promise.all([
                this.fetchWithCache('/api/executive-summary'),
                this.fetchWithCache('/api/cost-analysis')
            ]);

            this.updateExecutiveMetrics(executiveData);
            this.updateCostMetrics(costData);
            
            // Load the currently active tab
            const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-bs-target')?.replace('#', '');
            if (activeTab) {
                await this.loadTabData(activeTab);
            }

            this.updateTimestamp();
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Failed to load dashboard data', 'error');
        } finally {
            this.setLoadingState(false);
        }
    }

    /**
     * Handle tab changes with lazy loading
     */
    async handleTabChange(tabId) {
        console.log(`📊 Loading data for ${tabId} tab`);
        
        // Show loading state for the tab
        this.setTabLoadingState(tabId, true);
        
        try {
            await this.loadTabData(tabId);
        } catch (error) {
            console.error(`Error loading ${tabId} tab:`, error);
            this.showNotification(`Failed to load ${tabId} data`, 'error');
        } finally {
            this.setTabLoadingState(tabId, false);
        }
    }

    /**
     * Load data for specific tab
     */
    async loadTabData(tabId) {
        const loadingTasks = {
            'overview': () => this.loadOverviewData(),
            'merchant': () => this.loadMerchantData(),
            'optimization': () => this.loadOptimizationData(),
            'predictive': () => this.loadPredictiveData(),
            'data-quality': () => this.loadDataQualityData()
        };

        const loadTask = loadingTasks[tabId];
        if (loadTask) {
            await loadTask();
        }
    }

    /**
     * Load overview tab data
     */
    async loadOverviewData() {
        try {
            const [riskData, storeData, deptData, forecastData] = await Promise.allSettled([
                this.fetchWithCache('/api/top-risk-relays'),
                this.fetchWithCache('/api/store-performance'),
                this.fetchWithCache('/api/department-breakdown'),
                this.fetchWithCache('/api/weekly-forecast')
            ]);

            // Update components with error handling
            if (riskData.status === 'fulfilled') {
                this.updateRiskRelaysTable(riskData.value);
            }
            
            if (storeData.status === 'fulfilled') {
                this.updateStorePerformanceTable(storeData.value);
            }
            
            if (deptData.status === 'fulfilled') {
                this.updateDepartmentChart(deptData.value);
            }
            
            if (forecastData.status === 'fulfilled') {
                this.updateWorkloadForecastChart(forecastData.value);
            }

        } catch (error) {
            console.error('Error loading overview data:', error);
        }
    }

    /**
     * Load merchant analysis data
     */
    async loadMerchantData() {
        try {
            const [merchantData, requestData] = await Promise.allSettled([
                this.fetchWithCache('/api/merchant-analysis'),
                this.fetchWithCache('/api/merchant-requests')
            ]);

            if (merchantData.status === 'fulfilled') {
                this.updateMerchantCharts(merchantData.value);
            }
            
            if (requestData.status === 'fulfilled') {
                this.updateMerchantStatusCards(requestData.value);
            }

        } catch (error) {
            console.error('Error loading merchant data:', error);
        }
    }

    /**
     * Load optimization impact data
     */
    async loadOptimizationData() {
        try {
            const [optimizationData, opportunitiesData] = await Promise.allSettled([
                this.fetchWithCache('/api/optimization-impact'),
                this.fetchWithCache('/api/optimization-opportunities')
            ]);

            if (optimizationData.status === 'fulfilled') {
                this.updateOptimizationCharts(optimizationData.value);
            }
            
            if (opportunitiesData.status === 'fulfilled') {
                this.updateOptimizationOpportunities(opportunitiesData.value);
            }

        } catch (error) {
            console.error('Error loading optimization data:', error);
        }
    }

    /**
     * Load predictive insights data
     */
    async loadPredictiveData() {
        try {
            const [predictiveData, forecastData] = await Promise.allSettled([
                this.fetchWithCache('/api/predictive-insights'),
                this.fetchWithCache('/api/weekly-forecast')
            ]);

            if (predictiveData.status === 'fulfilled') {
                this.updatePredictiveCharts(predictiveData.value);
            }
            
            if (forecastData.status === 'fulfilled') {
                this.updateWeeklyForecastTable(forecastData.value);
            }

        } catch (error) {
            console.error('Error loading predictive data:', error);
        }
    }

    /**
     * Load data quality assessment data
     */
    async loadDataQualityData() {
        try {
            const response = await this.fetchWithCache('/api/data-quality');
            this.updateDataQualityCharts(response);
            this.updateDataQualityMetrics();
            
        } catch (error) {
            console.error('Error loading data quality data:', error);
        }
    }

    /**
     * Update executive summary metrics
     */
    updateExecutiveMetrics(data) {
        if (!data) return;

        // Update executive summary alert
        const alertElement = document.getElementById('executive-alert');
        const summaryText = document.getElementById('executive-summary-text');
        
        if (data.summary && alertElement && summaryText) {
            summaryText.textContent = data.summary;
            alertElement.style.display = 'block';
            this.animateElement(alertElement, 'slideInLeft');
        }

        // Update active requests count
        if (data.active_requests !== undefined) {
            this.animateCountUp('active-requests', data.active_requests);
        }
    }

    /**
     * Update cost analysis metrics
     */
    updateCostMetrics(data) {
        if (!data) return;

        const formatCurrency = (value) => {
            if (value >= 1000000) {
                return `$${(value / 1000000).toFixed(1)}M`;
            } else if (value >= 1000) {
                return `$${(value / 1000).toFixed(0)}K`;
            } else {
                return `$${Math.round(value)}`;
            }
        };

        // Animate metric updates
        if (data.baseline_cost !== undefined) {
            this.animateCountUp('total-cost', data.baseline_cost, formatCurrency);
        }
        
        if (data.savings !== undefined) {
            this.animateCountUp('potential-savings', data.savings, formatCurrency);
        }
        
        if (data.roi_percentage !== undefined) {
            this.animateCountUp('roi-percentage', data.roi_percentage, (v) => `${v.toFixed(1)}%`);
        }

        // Update trend indicators
        this.updateTrendIndicators(data);
    }

    /**
     * Update trend indicators with animations
     */
    updateTrendIndicators(data) {
        const trends = [
            { id: 'cost-trend', value: data.cost_trend, type: 'cost' },
            { id: 'savings-trend', value: data.savings_trend, type: 'savings' },
            { id: 'roi-trend', value: data.roi_trend, type: 'roi' }
        ];

        trends.forEach(trend => {
            const element = document.getElementById(trend.id);
            if (element && trend.value !== undefined) {
                const isPositive = trend.type === 'savings' || trend.type === 'roi' ? 
                    trend.value > 0 : trend.value < 0;
                
                element.className = `trend ${isPositive ? 'positive' : 'negative'}`;
                element.innerHTML = `
                    <i class="fas fa-arrow-${isPositive ? 'up' : 'down'}"></i> 
                    ${Math.abs(trend.value).toFixed(1)}% vs last period
                `;
            }
        });
    }

    /**
     * Update risk relays table with sorting and filtering
     */
    updateRiskRelaysTable(data) {
        const tbody = document.querySelector('#risk-relays-table tbody');
        if (!tbody) return;

        if (!data || data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted py-4">
                        <i class="fas fa-info-circle me-2"></i>
                        No high-risk relays identified
                    </td>
                </tr>
            `;
            return;
        }

        // Sort by risk score descending
        const sortedData = [...data].sort((a, b) => (b.Move_Risk_Score || 0) - (a.Move_Risk_Score || 0));

        tbody.innerHTML = sortedData.slice(0, 10).map((relay, index) => {
            const riskScore = relay.Move_Risk_Score || 0;
            const badgeClass = riskScore > 7 ? 'badge-danger' : 
                              riskScore > 4 ? 'badge-warning' : 'badge-success';
            
            return `
                <tr class="fade-in" style="animation-delay: ${index * 50}ms">
                    <td><strong>${relay.Relay_ID || 'N/A'}</strong></td>
                    <td>
                        <span class="badge badge-info badge-custom">
                            ${relay.DeptCat || 'N/A'}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${badgeClass} badge-custom">
                            ${riskScore.toFixed(1)}
                        </span>
                    </td>
                    <td>
                        <strong>$${(relay.Total_Move_Cost || 0).toLocaleString()}</strong>
                    </td>
                </tr>
            `;
        }).join('');

        // Add click handlers for row expansion
        this.addTableRowHandlers('#risk-relays-table');
    }

    /**
     * Update store performance table
     */
    updateStorePerformanceTable(data) {
        const tbody = document.querySelector('#store-performance-table tbody');
        if (!tbody) return;

        if (!data || data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted py-4">
                        <i class="fas fa-info-circle me-2"></i>
                        No store performance data available
                    </td>
                </tr>
            `;
            return;
        }

        // Sort by total cost descending
        const sortedData = [...data].sort((a, b) => (b.Total_Cost || 0) - (a.Total_Cost || 0));

        tbody.innerHTML = sortedData.slice(0, 10).map((store, index) => `
            <tr class="fade-in" style="animation-delay: ${index * 50}ms">
                <td><strong>${store.Store_ID || 'N/A'}</strong></td>
                <td>$${(store.Total_Cost || 0).toLocaleString()}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="me-2">${(store.Avg_Risk_Score || 0).toFixed(1)}</span>
                        <div class="progress-custom" style="width: 60px;">
                            <div class="progress-bar-custom" 
                                 style="width: ${Math.min((store.Avg_Risk_Score || 0) * 10, 100)}%">
                            </div>
                        </div>
                    </div>
                </td>
                <td>${store.Relay_Count || 0}</td>
            </tr>
        `).join('');

        this.addTableRowHandlers('#store-performance-table');
    }

    /**
     * Update department breakdown pie chart
     */
    updateDepartmentChart(data) {
        if (!data || data.length === 0) return;

        const chartData = [{
            values: data.map(d => d.Total_Move_Cost_sum || 0),
            labels: data.map(d => d.DeptCat || 'Unknown'),
            type: 'pie',
            hole: 0.4, // Donut chart
            marker: {
                colors: [
                    this.config.chartColors.primary,
                    this.config.chartColors.secondary,
                    this.config.chartColors.accent,
                    this.config.chartColors.success,
                    this.config.chartColors.warning,
                    this.config.chartColors.danger
                ],
                line: { color: '#fff', width: 2 }
            },
            textinfo: 'label+percent',
            textposition: 'outside',
            hovertemplate: '<b>%{label}</b><br>Cost: $%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
        }];

        const layout = {
            ...this.defaultLayout,
            title: {
                text: 'Cost Distribution by Department',
                font: { size: 16, color: this.config.chartColors.primary }
            },
            height: 400,
            showlegend: false,
            annotations: [{
                font: { size: 20, color: this.config.chartColors.primary },
                showarrow: false,
                text: `Total<br>$${data.reduce((sum, d) => sum + (d.Total_Move_Cost_sum || 0), 0).toLocaleString()}`,
                x: 0.5,
                y: 0.5
            }]
        };

        const config = {
            displayModeBar: false,
            responsive: true
        };

        Plotly.newPlot('department-pie', chartData, layout, config);
        this.chartInstances.set('department-pie', { data: chartData, layout, config });
    }

    /**
     * Update workload forecast chart
     */
    updateWorkloadForecastChart(data) {
        if (!data || data.length === 0) return;

        const dates = data.map(d => d.WK_End_Date);
        const costs = data.map(d => d.Projected_Cost || 0);
        const hours = data.map(d => d.Hours_Required || 0);

        const trace1 = {
            x: dates,
            y: costs,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Projected Cost',
            line: { 
                color: this.config.chartColors.primary,
                width: 3,
                shape: 'spline'
            },
            marker: { 
                size: 8,
                color: this.config.chartColors.primary,
                line: { color: '#fff', width: 2 }
            },
            yaxis: 'y',
            hovertemplate: '<b>Week: %{x}</b><br>Cost: $%{y:,.0f}<extra></extra>'
        };

        const trace2 = {
            x: dates,
            y: hours,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Hours Required',
            line: { 
                color: this.config.chartColors.secondary,
                width: 3,
                shape: 'spline'
            },
            marker: { 
                size: 8,
                color: this.config.chartColors.secondary,
                line: { color: '#fff', width: 2 }
            },
            yaxis: 'y2',
            hovertemplate: '<b>Week: %{x}</b><br>Hours: %{y:,.0f}<extra></extra>'
        };

        const layout = {
            ...this.defaultLayout,
            title: {
                text: 'Weekly Workload Forecast',
                font: { size: 16, color: this.config.chartColors.primary }
            },
            xaxis: {
                title: 'Week Ending Date',
                tickangle: -45,
                gridcolor: '#f0f0f0'
            },
            yaxis: {
                title: 'Projected Cost ($)',
                side: 'left',
                gridcolor: '#f0f0f0',
                tickformat: '$,.0f'
            },
            yaxis2: {
                title: 'Hours Required',
                side: 'right',
                overlaying: 'y',
                tickformat: ',.0f'
            },
            hovermode: 'x unified',
            height: 400
        };

        const config = {
            displayModeBar: 'hover',
            responsive: true
        };

        Plotly.newPlot('workload-forecast', [trace1, trace2], layout, config);
        this.chartInstances.set('workload-forecast', { data: [trace1, trace2], layout, config });
    }

    /**
     * Update merchant analysis charts
     */
    updateMerchantCharts(data) {
        if (!data) return;

        Object.entries(data).forEach(([chartKey, chartData]) => {
            const elementId = chartKey.replace(/_/g, '-') + '-chart';
            const element = document.getElementById(elementId);
            
            if (element && chartData) {
                try {
                    const plotData = JSON.parse(chartData);
                    Plotly.newPlot(element, plotData.data, plotData.layout, { responsive: true });
                    this.chartInstances.set(elementId, plotData);
                } catch (error) {
                    console.error(`Error updating chart ${elementId}:`, error);
                }
            }
        });
    }

    /**
     * Update merchant status cards
     */
    updateMerchantStatusCards(data) {
        if (!data || !Array.isArray(data)) return;

        // Aggregate request status data
        const statusCounts = data.reduce((acc, item) => {
            acc[item.Status] = (acc[item.Status] || 0) + item.Count;
            return acc;
        }, {});

        // Update individual cards
        this.animateCountUp('pending-requests', statusCounts['Pending'] || 0);
        this.animateCountUp('approved-requests', statusCounts['Approved'] || 0);
        this.animateCountUp('rejected-requests', statusCounts['Rejected'] || 0);

        // Calculate total cost impact
        const totalImpact = Object.values(statusCounts).reduce((sum, count) => sum + count, 0) * 2500; // Estimated cost per request
        this.animateCountUp('request-cost-impact', totalImpact, (v) => `$${(v / 1000).toFixed(0)}K`);
    }

    /**
     * Update weekly forecast table
     */
    updateWeeklyForecastTable(data) {
        const tbody = document.querySelector('#weekly-forecast-table tbody');
        if (!tbody) return;

        if (!data || data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="fas fa-info-circle me-2"></i>
                        No forecast data available
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.slice(0, 12).map((week, index) => {
            const cost = week.Projected_Cost || 0;
            const riskLevel = cost > 50000 ? 'High' : cost > 25000 ? 'Medium' : 'Low';
            const riskClass = riskLevel === 'High' ? 'badge-danger' : 
                             riskLevel === 'Medium' ? 'badge-warning' : 'badge-success';
            const riskIcon = riskLevel === 'High' ? 'fa-exclamation-triangle' : 
                            riskLevel === 'Medium' ? 'fa-exclamation-circle' : 'fa-check-circle';
            
            return `
                <tr class="fade-in" style="animation-delay: ${index * 50}ms">
                    <td><strong>${week.WK_End_Date || 'N/A'}</strong></td>
                    <td>$${cost.toLocaleString()}</td>
                    <td>${(week.Hours_Required || 0).toFixed(0)} hrs</td>
                    <td>${week.Relay_Count || 0}</td>
                    <td>
                        <span class="badge ${riskClass} badge-custom">
                            <i class="fas ${riskIcon} me-1"></i>
                            ${riskLevel}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }

    /**
     * Animate count up effect for metrics
     */
    animateCountUp(elementId, targetValue, formatter = null) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const startValue = 0;
        const duration = 1000;
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = startValue + (targetValue - startValue) * easeOutQuart;
            
            const displayValue = formatter ? formatter(currentValue) : Math.round(currentValue);
            element.textContent = displayValue;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    /**
     * Add animation class to element
     */
    animateElement(element, animationClass) {
        element.classList.add(animationClass);
        setTimeout(() => {
            element.classList.remove(animationClass);
        }, 1000);
    }

    /**
     * Set loading state for entire dashboard
     */
    setLoadingState(isLoading) {
        this.isLoading = isLoading;
        const overlay = document.getElementById('loading-overlay');
        
        if (overlay) {
            if (isLoading) {
                overlay.classList.remove('d-none');
            } else {
                overlay.classList.add('d-none');
            }
        }

        // Update connection status
        this.updateConnectionStatus(isLoading ? 'loading' : 'connected');
    }

    /**
     * Set loading state for specific tab
     */
    setTabLoadingState(tabId, isLoading) {
        const tabPane = document.getElementById(tabId);
        if (!tabPane) return;

        const loadingElements = tabPane.querySelectorAll('.loading');
        loadingElements.forEach(element => {
            element.style.display = isLoading ? 'flex' : 'none';
        });
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;

        const statusConfig = {
            connected: {
                class: 'badge bg-success',
                html: '<span class="status-indicator status-active"></span> Connected'
            },
            loading: {
                class: 'badge bg-warning',
                html: '<span class="status-indicator status-warning"></span> Loading...'
            },
            error: {
                class: 'badge bg-danger',
                html: '<span class="status-indicator status-error"></span> Error'
            },
            offline: {
                class: 'badge bg-secondary',
                html: '<span class="status-indicator status-error"></span> Offline'
            }
        };

        const config = statusConfig[status] || statusConfig.error;
        statusElement.className = config.class;
        statusElement.innerHTML = config.html;
    }

    /**
     * Fetch data with caching
     */
    async fetchWithCache(url, options = {}) {
        const cacheKey = `${url}-${JSON.stringify(options)}`;
        const cached = this.cache.get(cacheKey);
        const now = Date.now();

        // Return cached data if less than 2 minutes old
        if (cached && (now - cached.timestamp) < 120000) {
            return cached.data;
        }

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Cache the response
            this.cache.set(cacheKey, {
                data,
                timestamp: now
            });

            return data;

        } catch (error) {
            console.error(`Fetch error for ${url}:`, error);
            
            // Return cached data if available, even if expired
            if (cached) {
                console.warn(`Using stale cache for ${url}`);
                return cached.data;
            }
            
            throw error;
        }
    }

    /**
     * Refresh all dashboard data
     */
    async refreshAllData() {
        console.log('🔄 Refreshing all dashboard data...');
        
        // Clear cache
        this.cache.clear();
        
        // Show refresh animation
        const refreshBtn = document.getElementById('refresh-data');
        const refreshIcon = document.getElementById('refresh-icon');
        
        if (refreshIcon) {
            refreshIcon.classList.add('fa-spin');
        }

        try {
            // Call backend refresh endpoint
            const response = await fetch('/api/refresh-data', { method: 'POST' });
            const result = await response.json();
            
            if (result.status === 'success') {
                await this.loadInitialData();
                
                // Reload current tab
                const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-bs-target')?.replace('#', '');
                if (activeTab) {
                    await this.loadTabData(activeTab);
                }
                
                this.showNotification('Dashboard refreshed successfully', 'success');
            } else {
                throw new Error(result.message || 'Refresh failed');
            }

        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh dashboard data', 'error');
        } finally {
            if (refreshIcon) {
                refreshIcon.classList.remove('fa-spin');
            }
        }
    }

    /**
     * Start auto-refresh timer
     */
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        this.refreshTimer = setInterval(() => {
            if (!this.isLoading && document.visibilityState === 'visible') {
                console.log('⏰ Auto-refreshing dashboard...');
                this.refreshAllData();
            }
        }, this.config.refreshInterval);
    }

    /**
     * Stop auto-refresh timer
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Handle page visibility changes
     */
    handlePageVisible() {
        console.log('👁️ Page became visible');
        if (!this.refreshTimer) {
            this.startAutoRefresh();
        }
        // Refresh data if it's been more than 5 minutes
        const lastUpdate = Array.from(this.cache.values()).reduce((latest, cached) => 
            Math.max(latest, cached.timestamp), 0);
        
        if (Date.now() - lastUpdate > 300000) { // 5 minutes
            this.refreshAllData();
        }
    }

    /**
     * Handle page hidden
     */
    handlePageHidden() {
        console.log('🙈 Page became hidden');
        this.stopAutoRefresh();
    }

    /**
     * Handle network online
     */
    handleNetworkOnline() {
        console.log('🌐 Network came online');
        this.updateConnectionStatus('connected');
        this.refreshAllData();
    }

    /**
     * Handle network offline
     */
    handleNetworkOffline() {
        console.log('📡 Network went offline');
        this.updateConnectionStatus('offline');
        this.stopAutoRefresh();
    }

    /**
     * Handle window resize for responsive charts
     */
    handleWindowResize() {
        // Resize all Plotly charts
        this.chartInstances.forEach((chartData, elementId) => {
            const element = document.getElementById(elementId);
            if (element) {
                Plotly.Plots.resize(element);
            }
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        const shortcuts = {
            'r': () => this.refreshAllData(), // R key to refresh
            '1': () => this.switchTab('overview'), // Number keys to switch tabs
            '2': () => this.switchTab('merchant'),
            '3': () => this.switchTab('optimization'),
            '4': () => this.switchTab('predictive'),
            '5': () => this.switchTab('data-quality')
        };

        this.shortcuts = shortcuts;
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        // Only handle shortcuts when not in input fields
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }

        // Check for Ctrl/Cmd + key combinations
        if (event.ctrlKey || event.metaKey) {
            const handler = this.shortcuts[event.key.toLowerCase()];
            if (handler) {
                event.preventDefault();
                handler();
            }
        }
    }

    /**
     * Switch to specific tab
     */
    switchTab(tabId) {
        const tab = document.querySelector(`[data-bs-target="#${tabId}"]`);
        if (tab) {
            const tabInstance = new bootstrap.Tab(tab);
            tabInstance.show();
        }
    }

    /**
     * Setup intersection observer for lazy loading
     */
    setupIntersectionObserver() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    element.classList.add('fade-in');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '50px'
        });

        // Observe all chart containers and tables
        document.querySelectorAll('.chart-container, .data-table').forEach(element => {
            observer.observe(element);
        });
    }

    /**
     * Add interactive handlers to table rows
     */
    addTableRowHandlers(tableSelector) {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.addEventListener('click', () => {
                row.classList.toggle('table-active');
                // Could expand to show more details
            });
        });
    }

    /**
     * Setup chart event listeners
     */
    setupChartEventListeners() {
        // Global click handler for chart interactions
        document.addEventListener('plotly_click', (data) => {
            console.log('Chart clicked:', data);
            this.handleChartClick(data);
        });

        // Hover handlers
        document.addEventListener('plotly_hover', (data) => {
            this.handleChartHover(data);
        });
    }

    /**
     * Handle chart click events
     */
    handleChartClick(data) {
        // Implement drill-down functionality
        const point = data.points[0];
        if (point) {
            console.log('Clicked point:', point);
            // Could show detailed modal or filter other charts
        }
    }

    /**
     * Handle chart hover events
     */
    handleChartHover(data) {
        // Optional: Update other UI elements based on hover
    }

    /**
     * Show notification toast
     */
    showNotification(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        const typeConfig = {
            success: { class: 'alert-success', icon: 'fa-check-circle' },
            error: { class: 'alert-danger', icon: 'fa-exclamation-circle' },
            warning: { class: 'alert-warning', icon: 'fa-exclamation-triangle' },
            info: { class: 'alert-info', icon: 'fa-info-circle' }
        };

        const config = typeConfig[type] || typeConfig.info;
        
        toast.className = `alert ${config.class} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 350px; max-width: 500px;';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${config.icon} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.appendChild(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);

        // Add click handler to close button
        const closeBtn = toast.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            });
        }
    }

    /**
     * Update timestamp display
     */
    updateTimestamp() {
        const element = document.getElementById('update-time');
        if (element) {
            element.textContent = new Date().toLocaleString();
        }
    }

    /**
     * Debounce utility function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Cleanup resources
     */
    destroy() {
        console.log('🧹 Cleaning up dashboard resources...');
        
        // Stop auto-refresh
        this.stopAutoRefresh();
        
        // Remove event listeners
        this.eventListeners.forEach((listeners, key) => {
            listeners.forEach(({ target, event, handler }) => {
                target.removeEventListener(event, handler);
            });
        });
        
        // Clear caches
        this.cache.clear();
        this.chartInstances.clear();
        this.eventListeners.clear();
        
        console.log('✅ Dashboard cleanup completed');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new ModularRelayDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModularRelayDashboard;
}