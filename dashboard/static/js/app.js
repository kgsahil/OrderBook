/* eslint-disable no-alert */
/* global Chart */
window.tradingDashboard = function tradingDashboard() {
    return {
        ws: null,
        connected: false,
        connectionState: 'disconnected', // 'connecting', 'connected', 'disconnected', 'error'
        reconnectAttempts: 0,
        maxReconnectAttempts: 10,
        reconnectDelay: 3000,
        lastMessageTime: null,
        heartbeatInterval: null,
        heartbeatTimeout: null,
        selectedInstrumentId: '',
        selectedAgent: null,
        showAddInstrument: false,
        showAddAgent: false,
        showAgentDetails: false,
        showAddNews: false,
        agentTrades: [],
        agentDetails: null,

        instruments: [],
        agents: [],
        newsItems: [],
        orderbooks: {},
        bids: [],
        asks: [],
        bestBid: null,
        bestAsk: null,
        spread: null,
        maxDepthVolume: 0,  // For depth chart scaling
        currentPrice: null,
        currentSecondPrices: [], // Raw prices collected in current second
        candles: [], // Completed candles (one per second)
        priceChange: 0,
        priceChangeClass: '',
        candleInterval: null, // Interval for creating candles every second

        priceChart: null,
        chartUpdateScheduled: false,
        chartRetryCount: 0,
        chartData: {
            datasets: [{
                label: 'Price',
                data: []
            }]
        },

        recentOrderAnimations: new Set(),
        recentActivity: [],
        lastOrderbookSequence: 0,  // Track broadcast sequence numbers
        flashingAgents: {},  // Track agents that should flash (agent_id -> true)
        toasts: [],  // Toast notifications
        toastIdCounter: 0,
        performanceMetrics: {
            trades_per_second: 0,
            orders_per_second: 0,
            total_volume: 0,
            total_trades: 0,
            total_orders: 0,
            queue_full_count: 0,
            queue_capacity: 1024,
            queue_usage_pct: 0,
            uptime_seconds: 0,
            avg_trades_per_second: 0,
            avg_orders_per_second: 0
        },  // Performance metrics from orderbook

        newInstrument: { ticker: '', description: '', industry: '', initial_price: '' },
        newAgent: { name: '', personality: 'neutral', starting_capital: 100000 },
        newNews: { headline: '', content: '' },

        init() {
            this.connect();
            this.refreshAllData();
            this.loadPerformanceMetrics();
            // Refresh performance metrics every 2 seconds
            setInterval(() => {
                this.loadPerformanceMetrics();
            }, 2000);
            // Wait for LightweightCharts to be available
            this.waitForLightweightCharts(() => {
                this.setupChart();
                this.startCandleTimer();
            });
            
            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {
                this.stopHeartbeat();
                if (this.ws) {
                    this.ws.close(1000, 'Page unloading');
                }
            });
        },

        showToast(title, message, type = 'info', duration = 5000) {
            const toast = {
                id: ++this.toastIdCounter,
                title,
                message,
                type,
                visible: true
            };
            this.toasts.push(toast);
            
            // Auto-remove after duration
            setTimeout(() => {
                this.removeToast(toast.id);
            }, duration);
        },

        removeToast(id) {
            const toast = this.toasts.find(t => t.id === id);
            if (toast) {
                toast.visible = false;
                setTimeout(() => {
                    const index = this.toasts.findIndex(t => t.id === id);
                    if (index > -1) {
                        this.toasts.splice(index, 1);
                    }
                }, 300);
            }
        },

        formatUptime(seconds) {
            if (!seconds) return '0s';
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            if (hours > 0) {
                return `${hours}h ${minutes}m ${secs}s`;
            } else if (minutes > 0) {
                return `${minutes}m ${secs}s`;
            } else {
                return `${secs}s`;
            }
        },

        async loadPerformanceMetrics() {
            try {
                const response = await fetch('/api/performance');
                if (response.ok) {
                    const data = await response.json();
                    // Merge with existing to preserve structure
                    this.performanceMetrics = { ...this.performanceMetrics, ...data };
                } else {
                    const errorText = await response.text();
                    console.warn('Failed to load performance metrics:', response.status, errorText);
                }
            } catch (error) {
                console.error('Error loading performance metrics:', error);
                // Keep existing metrics on error
            }
        },

        waitForLightweightCharts(callback, maxAttempts = 50) {
            if (typeof LightweightCharts !== 'undefined') {
                callback();
                return;
            }
            if (maxAttempts <= 0) {
                console.error('LightweightCharts failed to load after multiple attempts');
                return;
            }
            setTimeout(() => {
                this.waitForLightweightCharts(callback, maxAttempts - 1);
            }, 100);
        },

        get calculatedMarketStats() {
            let totalVolume = 0;
            let totalOrders = 0;
            const spreads = [];

            for (const [, ob] of Object.entries(this.orderbooks)) {
                if (ob && ob.bids && ob.asks) {
                    const bids = Array.isArray(ob.bids) ? ob.bids : [];
                    const asks = Array.isArray(ob.asks) ? ob.asks : [];

                    bids.forEach((bid) => {
                        const qty = typeof bid === 'object' ? bid.quantity : 0;
                        const price = typeof bid === 'object' ? bid.price : bid;
                        totalVolume += qty * price;
                        totalOrders += typeof bid === 'object' ? (bid.orders || 1) : 1;
                    });

                    asks.forEach((ask) => {
                        const qty = typeof ask === 'object' ? ask.quantity : 0;
                        const price = typeof ask === 'object' ? ask.price : ask;
                        totalVolume += qty * price;
                        totalOrders += typeof ask === 'object' ? (ask.orders || 1) : 1;
                    });

                    if (bids.length > 0 && asks.length > 0) {
                        const bestBid = typeof bids[0] === 'object' ? bids[0].price : bids[0];
                        const bestAsk = typeof asks[0] === 'object' ? asks[0].price : asks[0];
                        const midPrice = (bestBid + bestAsk) / 2;
                        if (midPrice > 0) {
                            spreads.push((bestAsk - bestBid) / midPrice);
                        }
                    }
                }
            }

            return {
                totalVolume,
                totalOrders,
                avgSpread: spreads.length > 0 ? spreads.reduce((a, b) => a + b, 0) / spreads.length : null,
            };
        },

        get selectedInstrumentMeta() {
            if (!this.selectedInstrumentId) return null;
            return this.instruments.find((i) => i.symbol_id == this.selectedInstrumentId);
        },

        get sortedAgents() {
            return [...this.agents].sort(
                (a, b) => (b.total_value || b.cash || 0) - (a.total_value || a.cash || 0),
            );
        },

        get agentPositions() {
            return this.agentDetails?.positions || {};
        },

        connect() {
            if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
                console.log('WebSocket already connecting/connected, skipping new connection');
                return;
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            this.connectionState = 'connecting';
            this.connected = false;
            
            try {
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.connected = true;
                    this.connectionState = 'connected';
                    this.reconnectAttempts = 0;
                    this.reconnectDelay = 3000;
                    this.lastMessageTime = Date.now();
                    this.startHeartbeat();
                    this.refreshAllData();
                };

                this.ws.onmessage = (event) => {
                    this.lastMessageTime = Date.now();
                    this.resetHeartbeat();
                    
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
                        // Try to handle as text if not JSON
                        if (typeof event.data === 'string' && event.data.trim()) {
                            console.warn('Received non-JSON message:', event.data);
                        }
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.connectionState = 'error';
                    this.connected = false;
                    this.showToast('Connection Error', 'WebSocket connection error occurred', 'error', 3000);
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    this.connected = false;
                    this.connectionState = 'disconnected';
                    this.stopHeartbeat();
                    
                    // Only reconnect if it wasn't a manual close (code 1000)
                    if (event.code !== 1000) {
                        this.scheduleReconnect();
                    }
                };
            } catch (error) {
                console.error('Error creating WebSocket:', error);
                this.connectionState = 'error';
                this.scheduleReconnect();
            }
        },

        startHeartbeat() {
            this.stopHeartbeat();
            
            // Send ping every 30 seconds
            this.heartbeatInterval = setInterval(() => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    try {
                        // Send a ping message (some servers support this)
                        this.ws.send(JSON.stringify({ type: 'ping' }));
                    } catch (error) {
                        console.error('Error sending heartbeat:', error);
                    }
                }
            }, 30000);
            
            // Check if we've received a message in the last 60 seconds
            this.heartbeatTimeout = setInterval(() => {
                if (this.lastMessageTime && Date.now() - this.lastMessageTime > 60000) {
                    console.warn('No messages received in 60 seconds, connection may be stale');
                    this.connectionState = 'error';
                    // Force reconnect
                    if (this.ws) {
                        try {
                            this.ws.close();
                        } catch (e) {
                            console.error('Error closing stale connection:', e);
                        }
                    }
                    this.scheduleReconnect();
                }
            }, 10000); // Check every 10 seconds
        },

        stopHeartbeat() {
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }
            if (this.heartbeatTimeout) {
                clearInterval(this.heartbeatTimeout);
                this.heartbeatTimeout = null;
            }
        },

        resetHeartbeat() {
            // Reset the last message time
            this.lastMessageTime = Date.now();
        },

        scheduleReconnect() {
            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                console.error('Max reconnection attempts reached');
                this.showToast('Connection Failed', 'Unable to reconnect to server. Please refresh the page.', 'error', 10000);
                return;
            }
            
            this.reconnectAttempts++;
            const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
            console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
            
            setTimeout(() => {
                if (this.connectionState !== 'connected') {
                    this.connect();
                }
            }, delay);
        },

        handleMessage(message) {
            if (!message || typeof message !== 'object') {
                console.warn('Invalid message format:', message);
                return;
            }

            try {
                switch (message.type) {
                    case 'orderbooks':
                        this.updateOrderBooks(message.data);
                        break;
                    case 'instruments':
                        this.instruments = message.data || [];
                        this.ensureInstrumentSelection();
                        break;
                    case 'agents_snapshot':
                        this.agents = message.data || [];
                        break;
                    case 'order_placed':
                        this.handleOrderPlaced(message.data);
                        break;
                    case 'news':
                        if (message.data) {
                            this.newsItems.unshift(message.data);
                            if (this.newsItems.length > 50) {
                                this.newsItems.pop();
                            }
                        }
                        break;
                    case 'news_history':
                        this.newsItems = message.data || [];
                        break;
                    case 'pong':
                        // Heartbeat response
                        break;
                    case 'error':
                        console.error('Server error:', message.message || message);
                        this.showToast('Server Error', message.message || 'An error occurred', 'error');
                        break;
                    default:
                        // Unknown message type, log but don't break
                        if (message.type !== 'ping') { // Ignore ping messages
                            console.debug('Unknown message type:', message.type);
                        }
                        break;
                }
            } catch (error) {
                console.error('Error handling message:', error, 'Message:', message);
                // Don't break the connection on handler errors
            }
        },

        handleOrderPlaced(data) {
            const ticker = data.ticker || this.getTickerBySymbol(data.symbol_id) || `SYM ${data.symbol_id}`;
            this.recentActivity.push({
                agent: data.agent_name,
                side: data.side,
                quantity: data.quantity,
                price: data.price,
                ticker,
                time: data.timestamp || new Date().toISOString(),
            });

            if (this.recentActivity.length > 50) {
                this.recentActivity.shift();
            }

            // Flash the agent card that placed the order
            if (data.agent_id) {
                this.flashAgentCard(data.agent_id);
            } else if (data.agent_name) {
                // Fallback: find agent by name if agent_id not available
                const agent = this.agents.find(a => a.name === data.agent_name);
                if (agent && agent.agent_id) {
                    this.flashAgentCard(agent.agent_id);
                }
            }

            if (data.symbol_id == this.selectedInstrumentId) {
                this.animateOrderPlacement(data);

                // Collect price from executed trade for candle creation
                const tradePrice = parseFloat(data.price);
                if (tradePrice && !isNaN(tradePrice) && tradePrice > 0) {
                    const now = new Date(data.timestamp || new Date());
                    this.currentPrice = tradePrice;
                    
                    // Add to price history for current second
                    this.currentSecondPrices.push({
                        price: tradePrice,
                        timestamp: now.getTime()
                    });

                    // Update price change from last candle
                    if (this.candles.length > 0) {
                        const lastCandle = this.candles[this.candles.length - 1];
                        if (lastCandle && lastCandle.close > 0) {
                            this.priceChange = ((this.currentPrice - lastCandle.close) / lastCandle.close) * 100;
                            this.priceChangeClass = this.priceChange >= 0 ? 'text-green-400' : 'text-red-400';
                        }
                    } else {
                        this.priceChange = 0;
                        this.priceChangeClass = '';
                    }
                }
            }

            this.updateAgentActivity(data.agent_id, data);
        },

        flashAgentCard(agentId) {
            // Add agent to flashing object (reactive for Alpine.js)
            this.flashingAgents[agentId] = true;
            
            // Force reactivity update
            this.flashingAgents = { ...this.flashingAgents };
            
            // Remove after animation completes (0.8s)
            setTimeout(() => {
                delete this.flashingAgents[agentId];
                // Force reactivity update
                this.flashingAgents = { ...this.flashingAgents };
            }, 800);
        },

        getTickerBySymbol(symbolId) {
            const instrument = this.instruments.find((i) => i.symbol_id == symbolId);
            return instrument ? instrument.ticker : null;
        },

        animateOrderPlacement(data) {
            const side = data.side.toLowerCase();
            const price = parseFloat(data.price);
            const rows = side === 'buy' ? this.bids : this.asks;
            const rowIndex = rows.findIndex((r) => {
                const rowPrice = typeof r === 'object' ? r.price : r;
                return Math.abs(rowPrice - price) < 0.01;
            });

            if (rowIndex >= 0) {
                const key = `${side}-${rowIndex}`;
                this.recentOrderAnimations.add(key);
                setTimeout(() => this.recentOrderAnimations.delete(key), 600);
            }
        },

        updateAgentActivity(agentId, orderData) {
            const agent = this.agents.find((a) => a.agent_id === agentId);
            if (agent) {
                agent.lastActivity = {
                    time: new Date(orderData.timestamp),
                    side: orderData.side,
                    price: orderData.price,
                    quantity: orderData.quantity,
                };
            }
        },

        updateOrderBooks(data) {
            // Check for sequence gaps (debugging aid)
            if (data.sequence) {
                if (this.lastOrderbookSequence > 0 &&
                    data.sequence > this.lastOrderbookSequence + 1) {
                    const gap = data.sequence - this.lastOrderbookSequence;
                    console.warn(`⚠️ Orderbook sequence gap detected: ${this.lastOrderbookSequence} -> ${data.sequence} (missed ${gap - 1} messages)`);
                }
                this.lastOrderbookSequence = data.sequence;
            }

            this.orderbooks = data.data || data || {};
            if (this.selectedInstrumentId) {
                this.loadInstrumentOrderBook();
            }
        },

        loadInstrumentOrderBook() {
            if (!this.selectedInstrumentId) return;

            const symbolId = parseInt(this.selectedInstrumentId, 10);
            const ob = this.orderbooks[String(symbolId)] || this.orderbooks[symbolId];

            if (ob && ob.bids && ob.asks) {
                // console.log('DEBUG: Found orderbook for', symbolId, 'Bids:', ob.bids.length, 'Asks:', ob.asks.length);
                const oldBestBid = this.bestBid;
                const oldBestAsk = this.bestAsk;

                this.bids = Array.isArray(ob.bids) ? ob.bids : [];
                this.asks = Array.isArray(ob.asks) ? ob.asks : [];

                this.bids.sort((a, b) => b.price - a.price);
                this.asks.sort((a, b) => a.price - b.price);

                // Calculate cumulative volumes for depth chart
                let cumulativeBidVolume = 0;
                let cumulativeAskVolume = 0;
                this.bids.forEach(bid => {
                    cumulativeBidVolume += bid.quantity || 0;
                    bid.cumulativeVolume = cumulativeBidVolume;
                });
                this.asks.forEach(ask => {
                    cumulativeAskVolume += ask.quantity || 0;
                    ask.cumulativeVolume = cumulativeAskVolume;
                });
                
                // Find max volume for scaling
                this.maxDepthVolume = Math.max(
                    ...this.bids.map(b => b.cumulativeVolume || 0),
                    ...this.asks.map(a => a.cumulativeVolume || 0),
                    1
                );

                if (this.bids.length > 0) {
                    const bidPrice = typeof this.bids[0] === 'object' ? this.bids[0].price : this.bids[0];
                    this.bestBid = parseFloat(bidPrice);
                }

                if (this.asks.length > 0) {
                    const askPrice = typeof this.asks[0] === 'object' ? this.asks[0].price : this.asks[0];
                    this.bestAsk = parseFloat(askPrice);
                }

                if (this.bestBid && this.bestAsk) {
                    this.spread = this.bestAsk - this.bestBid;
                    const midPrice = (this.bestBid + this.bestAsk) / 2;

                    // Update current price display (but don't collect for candles - that comes from trades)
                    // Only update if we don't have a trade price yet
                    if (!this.currentPrice) {
                        this.currentPrice = midPrice;
                    }

                    if (oldBestBid && this.bestBid !== oldBestBid) {
                        this.animateOrder('bid');
                    }
                    if (oldBestAsk && this.bestAsk !== oldBestAsk) {
                        this.animateOrder('ask');
                    }
                }
            }
        },

        animateOrder(side) {
            const key = `${side}-0`;
            this.recentOrderAnimations.add(key);
            setTimeout(() => this.recentOrderAnimations.delete(key), 600);
        },

        onInstrumentChange() {
            // Clean up timer
            if (this.candleInterval) {
                clearInterval(this.candleInterval);
                this.candleInterval = null;
            }

            this.loadInstrumentOrderBook();
            this.currentSecondPrices = [];
            this.candles = [];

            // Clean up old chart
            if (this.priceChart) {
                this.priceChart.remove();
                this.priceChart = null;
                this.candlestickSeries = null;
            }

            this.setupChart();
            this.startCandleTimer();
        },

        startCandleTimer() {
            // Clear existing interval if any
            if (this.candleInterval) {
                clearInterval(this.candleInterval);
            }

            // Create a candle every second from collected prices
            this.candleInterval = setInterval(() => {
                this.createCandleFromPrices();
            }, 1000);
        },

        createCandleFromPrices() {
            if (!this.selectedInstrumentId) {
                // No instrument selected, don't create candles
                this.currentSecondPrices = [];
                return;
            }

            const now = new Date();
            const timeSeconds = Math.floor(now.getTime() / 1000);

            // Filter valid prices
            const prices = this.currentSecondPrices
                .map(p => p.price)
                .filter(p => p != null && !isNaN(p) && p > 0);
            
            let newCandle;

            if (prices.length === 0) {
                // No prices collected this second
                // Create a flat candle using last known price to maintain timeline
                if (this.candles.length > 0 && this.currentPrice) {
                    const lastCandle = this.candles[this.candles.length - 1];
                    newCandle = {
                        time: timeSeconds,
                        open: lastCandle.close,
                        high: lastCandle.close,
                        low: lastCandle.close,
                        close: lastCandle.close
                    };
                } else if (this.currentPrice) {
                    // First candle with no data, use current price
                    newCandle = {
                        time: timeSeconds,
                        open: this.currentPrice,
                        high: this.currentPrice,
                        low: this.currentPrice,
                        close: this.currentPrice
                    };
                } else {
                    // No price data at all, skip this candle
                    this.currentSecondPrices = [];
                    return;
                }
            } else {
                // Create candle from collected prices
                const open = prices[0];
                const close = prices[prices.length - 1];
                const high = Math.max(...prices);
                const low = Math.min(...prices);

                newCandle = {
                    time: timeSeconds,
                    open: open,
                    high: high,
                    low: low,
                    close: close
                };
            }

            // Add candle to array
            this.candles.push(newCandle);
            
            // Keep last 500 candles
            if (this.candles.length > 500) {
                this.candles.shift();
            }

            // Update chart with new candle
            this.updateChartWithNewCandle(newCandle);

            // Flush price history for next second
            this.currentSecondPrices = [];
        },

        updateChartWithNewCandle(candle) {
            if (!this.candlestickSeries) return;

            // Validate candle data
            if (!candle || 
                candle.time == null || 
                candle.open == null || 
                candle.high == null || 
                candle.low == null || 
                candle.close == null ||
                isNaN(candle.time) ||
                isNaN(candle.open) ||
                isNaN(candle.high) ||
                isNaN(candle.low) ||
                isNaN(candle.close)) {
                console.warn('Invalid candle data:', candle);
                return;
            }

            try {
                if (this.candles.length === 1) {
                    // First candle - set initial data
                    this.candlestickSeries.setData([candle]);
                } else {
                    // Update with new candle
                    this.candlestickSeries.update(candle);
                }
            } catch (e) {
                console.warn('Chart update failed, reloading all data:', e);
                // Reload all candles if update fails
                const validCandles = this.candles.filter(c => 
                    c && 
                    c.time != null && 
                    c.open != null && 
                    c.high != null && 
                    c.low != null && 
                    c.close != null &&
                    !isNaN(c.time) &&
                    !isNaN(c.open) &&
                    !isNaN(c.high) &&
                    !isNaN(c.low) &&
                    !isNaN(c.close)
                );
                if (validCandles.length > 0) {
                    this.candlestickSeries.setData(validCandles);
                }
            }
        },

        setupChart() {
            const container = document.getElementById('priceChart');
            if (!container) return;

            // Check if LightweightCharts is available
            if (typeof LightweightCharts === 'undefined') {
                console.error('LightweightCharts library is not loaded');
                // Try alternative name
                if (typeof window.lightweightCharts !== 'undefined') {
                    window.LightweightCharts = window.lightweightCharts;
                } else {
                    console.error('LightweightCharts library not found. Please check the script tag.');
                    return;
                }
            }

            // Clear container
            container.innerHTML = '';

            const chartOptions = {
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#9ca3af',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                width: container.clientWidth,
                height: container.clientHeight,
                timeScale: {
                    timeVisible: true,
                    secondsVisible: true,
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                },
                rightPriceScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                },
            };

            try {
            this.priceChart = LightweightCharts.createChart(container, chartOptions);

                if (!this.priceChart) {
                    console.error('createChart returned null/undefined');
                    return;
                }

                if (typeof this.priceChart.addCandlestickSeries !== 'function') {
                    console.error('addCandlestickSeries is not a function');
                    return;
                }

            this.candlestickSeries = this.priceChart.addCandlestickSeries({
                upColor: '#22c55e',
                downColor: '#ef4444',
                borderVisible: false,
                wickUpColor: '#22c55e',
                wickDownColor: '#ef4444',
            });
            } catch (error) {
                console.error('Error setting up chart:', error);
                return;
            }

            // Set initial data if available (filter out invalid candles)
            if (this.candles.length > 0) {
                const validCandles = this.candles.filter(c => 
                    c && 
                    c.time != null && 
                    c.open != null && 
                    c.high != null && 
                    c.low != null && 
                    c.close != null &&
                    !isNaN(c.time) &&
                    !isNaN(c.open) &&
                    !isNaN(c.high) &&
                    !isNaN(c.low) &&
                    !isNaN(c.close)
                );
                if (validCandles.length > 0) {
                    this.candlestickSeries.setData(validCandles);
                }
            }

            // Handle resize
            const resizeObserver = new ResizeObserver(entries => {
                if (entries.length === 0 || entries[0].target !== container) { return; }
                const newRect = entries[0].contentRect;
                this.priceChart.applyOptions({ width: newRect.width, height: newRect.height });
            });
            resizeObserver.observe(container);
        },

        // updateChart is no longer needed - candles are created by timer
        // Keeping for backwards compatibility but it's now handled by updateChartWithNewCandle
        updateChart() {
            // Chart updates are now handled by the per-second timer
            // This method is kept for compatibility but does nothing
        },

        applyChartData() {
            // No longer needed as separate step, handled in updateChart
        },

        handleChartError(error) {
            console.error('Chart error:', error);
        },

        async loadInstruments() {
            try {
                const response = await fetch('/api/instruments');
                this.instruments = await response.json();
                this.ensureInstrumentSelection();
            } catch (error) {
                console.error('Failed to load instruments:', error);
            }
        },

        refreshAllData() {
            this.loadInstruments();
            this.loadAgents();
            this.loadNews();
        },

        ensureInstrumentSelection() {
            if (!this.instruments || this.instruments.length === 0) {
                this.selectedInstrumentId = null;
                this.currentSecondPrices = [];
                this.candles = [];
                return;
            }

            const stillValid =
                this.selectedInstrumentId && this.instruments.some((inst) => inst.symbol_id == this.selectedInstrumentId);

            if (!stillValid) {
                this.selectedInstrumentId = this.instruments[0].symbol_id;
                this.currentSecondPrices = [];
                this.candles = [];
                this.loadInstrumentOrderBook();
            }
        },

        async loadAgents() {
            try {
                const response = await fetch('/api/agents');
                this.agents = await response.json();
            } catch (error) {
                console.error('Failed to load agents:', error);
            }
        },

        async loadNews() {
            try {
                const response = await fetch('/api/news?limit=20');
                if (response.ok) {
                    this.newsItems = await response.json();
                }
            } catch (error) {
                console.error('Failed to load news:', error);
            }
        },

        formatCurrency(value) {
            if (value == null) return '--';
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }).format(value);
        },

        formatPrice(value) {
            if (value == null) return '--';
            return parseFloat(value).toFixed(2);
        },

        formatQuantity(value) {
            if (value == null) return '--';
            return parseFloat(value).toFixed(0);
        },

        formatTime(date) {
            if (!date) return '';
            const d = new Date(date);
            return d.toLocaleTimeString();
        },

        getAgentColor(personality) {
            const colors = {
                aggressive: '#ef4444, #dc2626',
                conservative: '#3b82f6, #2563eb',
                momentum: '#8b5cf6, #7c3aed',
                news_trader: '#f59e0b, #d97706',
                market_maker: '#10b981, #059669',
                neutral: '#6b7280, #4b5563',
                short_seller: '#dc2626, #991b1b',
            };
            return colors[personality] || colors.neutral;
        },

        getPersonalityClass(personality) {
            const classes = {
                aggressive: 'bg-red-500/20 text-red-300',
                conservative: 'bg-blue-500/20 text-blue-300',
                momentum: 'bg-purple-500/20 text-purple-300',
                news_trader: 'bg-amber-500/20 text-amber-300',
                market_maker: 'bg-green-500/20 text-green-300',
                neutral: 'bg-gray-500/20 text-gray-300',
                short_seller: 'bg-red-600/20 text-red-300',
            };
            return classes[personality] || classes.neutral;
        },

        isRecentActivity(activity) {
            if (!activity || !activity.time) return false;
            const timeDiff = new Date() - new Date(activity.time);
            return timeDiff < 2000;
        },

        async addInstrument() {
            if (!this.newInstrument.ticker || !this.newInstrument.initial_price) {
                this.showToast('Validation Error', 'Ticker and initial price are required', 'error');
                return;
            }

            try {
                const response = await fetch('/api/instruments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ticker: this.newInstrument.ticker,
                        description: this.newInstrument.description || '',
                        industry: this.newInstrument.industry || '',
                        initial_price: parseFloat(this.newInstrument.initial_price),
                    }),
                });

                if (response.ok) {
                    const instrument = await response.json();
                    this.instruments.push(instrument);
                    this.newInstrument = { ticker: '', description: '', industry: '', initial_price: '' };
                    this.showAddInstrument = false;
                    this.showToast('Success', 'Instrument added successfully!', 'success');
                } else {
                    const error = await response.json();
                    this.showToast('Error', error.detail || 'Failed to add instrument', 'error');
                }
            } catch (error) {
                console.error('Error adding instrument:', error);
                this.showToast('Error', 'Failed to add instrument', 'error');
            }
        },

        async addAgent() {
            if (!this.newAgent.name || !this.newAgent.personality || !this.newAgent.starting_capital) {
                this.showToast('Validation Error', 'Name, personality, and starting capital are required', 'error');
                return;
            }

            try {
                const response = await fetch('/api/agents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: this.newAgent.name,
                        personality: this.newAgent.personality,
                        starting_capital: parseFloat(this.newAgent.starting_capital),
                    }),
                });

                if (response.ok) {
                    const agent = await response.json();
                    this.agents.push(agent);
                    this.newAgent = { name: '', personality: 'neutral', starting_capital: 100000 };
                    this.showAddAgent = false;
                    this.showToast('Success', 'Agent created successfully! Note: Agent must connect via WebSocket to start trading.', 'success', 7000);
                } else {
                    const error = await response.json();
                    this.showToast('Error', error.detail || 'Failed to create agent', 'error');
                }
            } catch (error) {
                console.error('Error adding agent:', error);
                this.showToast('Error', 'Failed to create agent', 'error');
            }
        },

        async showAgentDetailsModal(agent) {
            this.selectedAgent = agent;
            this.showAgentDetails = true;
            this.agentDetails = { positions: {} };
            await this.loadAgentDetails(agent.agent_id);
        },

        async loadAgentDetails(agentId) {
            try {
                const agentResponse = await fetch(`/api/agents/${agentId}`);
                if (agentResponse.ok) {
                    this.agentDetails = await agentResponse.json();
                }

                const tradesResponse = await fetch(`/api/agents/${agentId}/trades?limit=50`);
                if (tradesResponse.ok) {
                    this.agentTrades = await tradesResponse.json();
                }
            } catch (error) {
                console.error('Error loading agent details:', error);
            }
        },

        async publishNews() {
            if (!this.newNews.headline || !this.newNews.content) {
                this.showToast('Validation Error', 'Headline and content are required', 'error');
                return;
            }

            try {
                const response = await fetch('/api/news', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        headline: this.newNews.headline,
                        content: this.newNews.content,
                    }),
                });

                if (response.ok) {
                    this.newNews = { headline: '', content: '' };
                    this.showAddNews = false;
                    this.showToast('Success', 'News published successfully!', 'success');
                } else {
                    const error = await response.json();
                    this.showToast('Error', error.detail || 'Failed to publish news', 'error');
                }
            } catch (error) {
                console.error('Error publishing news:', error);
                this.showToast('Error', 'Failed to publish news', 'error');
            }
        },
    };
};

