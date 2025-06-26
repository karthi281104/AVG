document.addEventListener('DOMContentLoaded', function() {
    // Initialize AOS animation library
    AOS.init({
        duration: 1000,
        once: true,
        easing: 'ease'
    });

    // Initialize the page components
    initializePage();

    // Responsive header handling
    window.addEventListener('scroll', function() {
        const header = document.querySelector('header');
        header.classList.toggle('scrolled', window.scrollY > 50);

        // Back to top button visibility
        const backToTop = document.querySelector('.back-to-top');
        if (backToTop) {
            if (window.scrollY > 300) {
                backToTop.classList.add('show');
            } else {
                backToTop.classList.remove('show');
            }
        }
    });

    // Activate back to top button
    const backToTop = document.querySelector('.back-to-top');
    if (backToTop) {
        backToTop.addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Price alert toggle button
    const alertToggleBtn = document.getElementById('alertToggleBtn');
    const alertPopup = document.getElementById('alertPopup');
    const closeBtn = document.querySelector('.close-btn');

    if (alertToggleBtn && alertPopup) {
        alertToggleBtn.addEventListener('click', function() {
            alertPopup.classList.toggle('show');
        });

        closeBtn.addEventListener('click', function() {
            alertPopup.classList.remove('show');
        });

        // Close popup when clicking outside
        document.addEventListener('click', function(event) {
            if (!alertPopup.contains(event.target) && !alertToggleBtn.contains(event.target)) {
                alertPopup.classList.remove('show');
            }
        });
    }

    // Set price alert functionality
    const setAlertBtn = document.getElementById('setAlertBtn');
    const alertPriceInput = document.getElementById('alertPrice');
    const alertList = document.getElementById('alertList');

    if (setAlertBtn && alertPriceInput && alertList) {
        setAlertBtn.addEventListener('click', function() {
            const price = parseFloat(alertPriceInput.value);
            if (!isNaN(price) && price > 0) {
                addAlert(price);
                alertPriceInput.value = '';
            }
        });
    }

    // Gold calculator functionality
    const calculateBtn = document.getElementById('calculateBtn');
    const goldWeight = document.getElementById('goldWeight');
    const goldPurity = document.getElementById('goldPurity');
    const calculatedValue = document.getElementById('calculatedValue');

    if (calculateBtn && goldWeight && goldPurity && calculatedValue) {
        calculateBtn.addEventListener('click', function() {
            const weight = parseFloat(goldWeight.value);
            const purity = parseFloat(goldPurity.value);

            if (!isNaN(weight) && weight > 0) {
                const currentGoldPrice = getCurrentGoldPrice();
                const value = (currentGoldPrice / 10) * weight * purity;
                calculatedValue.textContent = value.toLocaleString('en-IN', {
                    maximumFractionDigits: 2,
                    minimumFractionDigits: 2
                });
            }
        });
    }

    // Chart period buttons
    const periodButtons = document.querySelectorAll('.btn-chart');

    if (periodButtons.length > 0) {
        periodButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                periodButtons.forEach(btn => btn.classList.remove('active'));
                // Add active class to clicked button
                this.classList.add('active');

                // Update chart with the selected period
                const period = this.getAttribute('data-period');
                updateGoldPriceChart(period);
            });
        });
    }
});

// Initialize the page with data and charts
function initializePage() {
    // Start the real-time gold price updates
    startRealTimeUpdates();

    // Initialize the gold price history chart
    initializeGoldPriceChart();

    // Initialize the investment comparison chart
    initializeInvestmentComparisonChart();

    // Load gold rates by type
    loadGoldRatesByType();

    // Load gold rates by city
    loadGoldRatesByCities();

    // Load market insights data
    loadMarketInsights();
}

// Simulate real-time gold price updates
function startRealTimeUpdates() {
    // Set initial data
    updateGoldPrice({
        price: 68750, // Price in INR
        change: 250,   // Change in INR
        changePercent: 0.36, // Change in percentage
        trend: 'up',   // 'up' or 'down'
        lastUpdated: new Date()
    });

    // Update every 30 seconds (30000 ms)
    setInterval(function() {
        simulateGoldPriceChange();
    }, 30000);
}

// Simulate a change in gold price
function simulateGoldPriceChange() {
    const currentPrice = getCurrentGoldPrice();
    // Simulate small realistic changes (-0.2% to +0.2%)
    const changePercent = (Math.random() * 0.4 - 0.2).toFixed(2);
    const priceChange = Math.round(currentPrice * changePercent / 100);
    const newPrice = Math.round(currentPrice + priceChange);

    updateGoldPrice({
        price: newPrice,
        change: Math.abs(priceChange),
        changePercent: Math.abs(changePercent),
        trend: priceChange >= 0 ? 'up' : 'down',
        lastUpdated: new Date()
    });
}

// Get the current gold price
function getCurrentGoldPrice() {
    const goldPriceElement = document.getElementById('gold-price-value');
    if (goldPriceElement) {
        const priceText = goldPriceElement.textContent.replace(/[^0-9]/g, '');
        return parseInt(priceText) || 68750; // Default to 68750 if parsing fails
    }
    return 68750; // Default price
}

// Update the gold price display
function updateGoldPrice(data) {
    const goldPriceElement = document.getElementById('gold-price-value');
    const priceChangeElement = document.getElementById('price-change');
    const changeValueElement = document.getElementById('change-value');
    const changePercentElement = document.getElementById('change-percentage');
    const lastUpdatedElement = document.getElementById('last-updated');

    if (goldPriceElement && priceChangeElement && changeValueElement &&
        changePercentElement && lastUpdatedElement) {

        // Format the price with commas for Indian numbering system (e.g., 68,750)
        goldPriceElement.textContent = '₹ ' + data.price.toLocaleString('en-IN');

        // Update change values
        changeValueElement.textContent = '₹ ' + data.change.toLocaleString('en-IN');
        changePercentElement.textContent = '(' + data.changePercent + '%)';

        // Set the trend class (up or down)
        priceChangeElement.className = 'price-change';
        priceChangeElement.classList.add(data.trend);

        // Update the icon
        const iconElement = priceChangeElement.querySelector('i');
        if (iconElement) {
            iconElement.className = data.trend === 'up' ? 'fas fa-caret-up' : 'fas fa-caret-down';
        }

        // Update last updated time
        lastUpdatedElement.textContent = formatDateTime(data.lastUpdated);
    }

    // Check and trigger price alerts
    checkPriceAlerts(data.price);
}

// Check if any price alerts should be triggered
function checkPriceAlerts(currentPrice) {
    // Get stored alerts from localStorage
    const alerts = getStoredAlerts();

    // Check each alert and trigger notification if price threshold is reached
    alerts.forEach((alert, index) => {
        if ((alert.direction === 'above' && currentPrice >= alert.price) ||
            (alert.direction === 'below' && currentPrice <= alert.price)) {
            // Trigger notification
            showNotification(`Gold Price Alert: ₹${currentPrice.toLocaleString('en-IN')}`,
                            `Gold price has reached your alert threshold of ₹${alert.price.toLocaleString('en-IN')}.`);

            // Remove triggered alert
            alerts.splice(index, 1);
            storeAlerts(alerts);

            // Update the alerts list in the UI
            renderAlertsList();
        }
    });
}

// Show a browser notification
function showNotification(title, message) {
    // Check if the browser supports notifications
    if (!("Notification" in window)) {
        alert(`${title}: ${message}`);
    }
    // Check if permission is already granted
    else if (Notification.permission === "granted") {
        const notification = new Notification(title, {
            body: message,
            icon: 'https://img.icons8.com/color/48/000000/gold-bars.png'
        });
    }
    // Otherwise, ask for permission
    else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                const notification = new Notification(title, {
                    body: message,
                    icon: 'https://img.icons8.com/color/48/000000/gold-bars.png'
                });
            }
        });
    }
}

// Add a new price alert
function addAlert(price) {
    // Get the current price to determine if alert is for above or below
    const currentPrice = getCurrentGoldPrice();
    const direction = price > currentPrice ? 'above' : 'below';

    // Create alert object
    const alert = {
        id: Date.now(), // Use timestamp as ID
        price: price,
        direction: direction,
        createdAt: new Date()
    };

    // Get existing alerts
    const alerts = getStoredAlerts();

    // Add new alert
    alerts.push(alert);

    // Store updated alerts
    storeAlerts(alerts);

    // Update the UI
    renderAlertsList();

    // Show confirmation
    showToast(`Alert set for ₹${price.toLocaleString('en-IN')}`);
}

// Delete a price alert
function deleteAlert(alertId) {
    let alerts = getStoredAlerts();

    // Filter out the alert with the specified ID
    alerts = alerts.filter(alert => alert.id !== alertId);

    // Store updated alerts
    storeAlerts(alerts);

    // Update the UI
    renderAlertsList();

    // Show confirmation
    showToast('Alert removed');
}

// Get stored alerts from localStorage
function getStoredAlerts() {
    const storedAlerts = localStorage.getItem('goldPriceAlerts');
    return storedAlerts ? JSON.parse(storedAlerts) : [];
}

// Store alerts to localStorage
function storeAlerts(alerts) {
    localStorage.setItem('goldPriceAlerts', JSON.stringify(alerts));
}

// Render the alerts list in the UI
function renderAlertsList() {
    const alertList = document.getElementById('alertList');
    if (!alertList) return;

    // Get stored alerts
    const alerts = getStoredAlerts();

    // Clear existing content
    alertList.innerHTML = '';

    if (alerts.length === 0) {
        alertList.innerHTML = '<p class="text-muted text-center">No alerts set</p>';
        return;
    }

    // Add each alert to the list
    alerts.forEach(alert => {
        const alertItem = document.createElement('div');
        alertItem.className = 'alert-item';

        const directionSymbol = alert.direction === 'above' ? '↑' : '↓';
        const directionClass = alert.direction === 'above' ? 'text-success' : 'text-danger';

        alertItem.innerHTML = `
            <div class="alert-price">
                <span class="${directionClass}">${directionSymbol}</span> 
                ₹${alert.price.toLocaleString('en-IN')}
            </div>
            <div class="alert-delete" data-id="${alert.id}">
                <i class="fas fa-times"></i>
            </div>
        `;

        // Add event listener for delete button
        alertItem.querySelector('.alert-delete').addEventListener('click', function() {
            const alertId = parseInt(this.getAttribute('data-id'));
            deleteAlert(alertId);
        });

        alertList.appendChild(alertItem);
    });
}

// Show a toast message
function showToast(message) {
    // Create toast element if it doesn't exist
    let toast = document.querySelector('.toast-message');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast-message';
        document.body.appendChild(toast);
    }

    // Set message and show toast
    toast.textContent = message;
    toast.classList.add('show');

    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Format date and time
function formatDateTime(date) {
    return date.toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Initialize the gold price history chart
function initializeGoldPriceChart() {
    const chartData = generateHistoricalPriceData();

    const options = {
        series: [{
            name: 'Gold Price (₹/10g)',
            data: chartData.prices
        }],
        chart: {
            height: 400,
            type: 'area',
            fontFamily: 'Poppins, sans-serif',
            toolbar: {
                show: false
            },
            zoom: {
                enabled: false
            },
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            }
        },
        colors: ['#d4af37'],
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.7,
                opacityTo: 0.2,
                stops: [0, 90, 100]
            }
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        grid: {
            borderColor: '#f1f1f1',
            row: {
                colors: ['transparent', 'transparent'],
                opacity: 0.5
            }
        },
        markers: {
            size: 4,
            colors: ['#d4af37'],
            strokeColors: '#fff',
            strokeWidth: 2,
            hover: {
                size: 7
            }
        },
        xaxis: {
            categories: chartData.dates,
            labels: {
                style: {
                    colors: '#888',
                    fontSize: '12px',
                    fontFamily: 'Poppins, sans-serif',
                    fontWeight: 400
                }
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: {
            labels: {
                formatter: function(value) {
                    return '₹' + value.toLocaleString('en-IN');
                },
                style: {
                    colors: '#888',
                    fontSize: '12px',
                    fontFamily: 'Poppins, sans-serif',
                    fontWeight: 400
                }
            }
        },
        tooltip: {
            theme: 'light',
            y: {
                formatter: function(value) {
                    return '₹' + value.toLocaleString('en-IN') + ' per 10g';
                }
            }
        }
    };

    const chart = new ApexCharts(document.querySelector("#gold-price-chart"), options);
    chart.render();

    // Save chart instance for updates
    window.goldPriceChart = chart;
}

// Update the gold price chart with a different time period
function updateGoldPriceChart(period) {
    if (!window.goldPriceChart) return;

    const chartData = generateHistoricalPriceData(period);

    window.goldPriceChart.updateOptions({
        series: [{
            data: chartData.prices
        }],
        xaxis: {
            categories: chartData.dates
        }
    });
}

// Generate historical price data for the chart
function generateHistoricalPriceData(period = '1m') {
    const dates = [];
    const prices = [];
    const currentPrice = getCurrentGoldPrice();
    let dataPoints = 30; // Default to 1 month

    switch (period) {
        case '1d':
            dataPoints = 24;
            break;
        case '1w':
            dataPoints = 7;
            break;
        case '1m':
            dataPoints = 30;
            break;
        case '3m':
            dataPoints = 90;
            break;
        case '1y':
            dataPoints = 12;
            break;
    }

    // Generate realistic price data
    let price = currentPrice;
    const volatility = period === '1d' ? 0.001 : period === '1w' ? 0.005 : period === '1m' ? 0.01 : 0.03;
    const trend = 0.001; // Small upward trend

    // Generate dates and prices
    for (let i = dataPoints; i > 0; i--) {
        let date = new Date();

        if (period === '1d') {
            date.setHours(date.getHours() - i);
            dates.push(date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
        } else if (period === '1w') {
            date.setDate(date.getDate() - i);
            dates.push(date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
        } else if (period === '1m') {
            date.setDate(date.getDate() - i);
            dates.push(date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
        } else if (period === '3m') {
            date.setDate(date.getDate() - i);
            dates.push(date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
        } else if (period === '1y') {
            date.setMonth(date.getMonth() - i);
            dates.push(date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }));
        }

        // Calculate previous price with random variation, but maintaining a slight upward trend
        const change = price * (Math.random() * volatility * 2 - volatility + trend);
        price = Math.round(price - change);
        prices.push(price);
    }

    // Add current price as the last point
    prices[prices.length - 1] = currentPrice;

    return { dates, prices };
}

// Initialize the investment comparison chart
function initializeInvestmentComparisonChart() {
    const options = {
        series: [{
            name: 'Gold',
            data: [15, 18, 22, 25, 31, 35, 42]
        }, {
            name: 'Stocks',
            data: [12, 19, 16, 28, 25, 33, 40]
        }, {
            name: 'Fixed Deposits',
            data: [10, 11, 12, 13, 14, 15, 16]
        }],
        chart: {
            height: 350,
            type: 'line',
            toolbar: {
                show: false
            },
            zoom: {
                enabled: false
            }
        },
        colors: ['#d4af37', '#8a2be2', '#36a2eb'],
        dataLabels: {
            enabled: false
        },
        stroke: {
            width: [3, 3, 3],
            curve: 'smooth',
            dashArray: [0, 0, 0]
        },
        title: {
            text: '5 Year Performance Comparison',
            align: 'left',
            style: {
                fontSize: '14px',
                fontWeight: 600,
                fontFamily: 'Poppins, sans-serif'
            }
        },
        legend: {
            tooltipHoverFormatter: function(val, opts) {
                return val + ' - <strong>' + opts.w.globals.series[opts.seriesIndex][opts.dataPointIndex] + '% return</strong>';
            },
            position: 'top'
        },
        markers: {
            size: 0,
            hover: {
                sizeOffset: 6
            }
        },
        xaxis: {
            categories: ['2020', '2021', '2022', '2023', '2024', '2025', '2026'],
            labels: {
                style: {
                    colors: '#888',
                    fontSize: '12px',
                    fontFamily: 'Poppins, sans-serif',
                    fontWeight: 400
                }
            }
        },
        yaxis: {
            title: {
                text: 'Return (%)'
            },
            labels: {
                formatter: function(value) {
                    return value + '%';
                },
                style: {
                    colors: '#888',
                    fontSize: '12px',
                    fontFamily: 'Poppins, sans-serif',
                    fontWeight: 400
                }
            }
        },
        tooltip: {
            y: {
                formatter: function(value) {
                    return value + '% return';
                }
            }
        },
        grid: {
            borderColor: '#f1f1f1'
        }
    };

    const chart = new ApexCharts(document.querySelector("#investment-comparison-chart"), options);
    chart.render();
}

// Load gold rates by type/purity
function loadGoldRatesByType() {
    const tbody = document.getElementById('gold-rates-tbody');
    if (!tbody) return;

    // Clear any existing content
    tbody.innerHTML = '';

    // Get current gold price (24K)
    const goldPrice24K = getCurrentGoldPrice();

    // Define gold types and purities
    const goldTypes = [
        { type: '24K Gold', purity: '99.9%', ratio: 1 },
        { type: '22K Gold', purity: '91.6%', ratio: 0.916 },
        { type: '18K Gold', purity: '75%', ratio: 0.75 },
        { type: '14K Gold', purity: '58.5%', ratio: 0.585 }
    ];

    // Generate table rows
    goldTypes.forEach(gold => {
        const pricePerGram = Math.round(goldPrice24K / 10 * gold.ratio);
        const pricePer10Gram = pricePerGram * 10;

        // Random change between -100 and 100
        const change = Math.floor(Math.random() * 200 - 100);
        const trend = change >= 0 ? 'up' : 'down';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${gold.type}</strong></td>
            <td>${gold.purity}</td>
            <td>₹ ${pricePerGram.toLocaleString('en-IN')}</td>
            <td>₹ ${pricePer10Gram.toLocaleString('en-IN')}</td>
            <td>
                <span class="trend-${trend}">
                    <i class="fas fa-caret-${trend}"></i>
                    ₹ ${Math.abs(change).toLocaleString('en-IN')}
                </span>
            </td>
        `;

        tbody.appendChild(row);
    });
}

// Load gold rates by cities
function loadGoldRatesByCities() {
    const container = document.getElementById('city-rates-container');
    if (!container) return;

    // Clear any existing content
    container.innerHTML = '';

    // Get current base gold price
    const baseGoldPrice = getCurrentGoldPrice();

    // Define Indian cities with slight price variations
    const cities = [
        { name: 'Mumbai', variation: 0 },      // Use as base
        { name: 'Delhi', variation: -200 },    // Slightly cheaper
        { name: 'Kolkata', variation: -100 },  // Slightly cheaper
        { name: 'Chennai', variation: 150 },   // Slightly more expensive
        { name: 'Bangalore', variation: 300 }, // More expensive
        { name: 'Hyderabad', variation: 50 },  // Slightly more expensive
        { name: 'Ahmedabad', variation: -150 },// Cheaper
        { name: 'Jaipur', variation: -50 },    // Slightly cheaper
        { name: 'Lucknow', variation: -120 }   // Cheaper
    ];

    // Generate cards for each city with price variations
    cities.forEach(city => {
        const cityPrice = baseGoldPrice + city.variation;

        const cityCard = document.createElement('div');
        cityCard.className = 'col-md-4 mb-4';
        cityCard.setAttribute('data-aos', 'fade-up');

        cityCard.innerHTML = `
            <div class="city-rate-card">
                <div class="city-card-header">
                    <i class="fas fa-map-marker-alt"></i>
                    <h3>${city.name}</h3>
                </div>
                <div class="city-card-body">
                    <div class="city-price">₹ ${cityPrice.toLocaleString('en-IN')}</div>
                    <span class="city-price-unit">per 10g (24K)</span>
                </div>
            </div>
        `;

        container.appendChild(cityCard);
    });
}

// Load market insights data
function loadMarketInsights() {
    // Exchange rate
    const exchangeRateElement = document.getElementById('exchange-rate');
    if (exchangeRateElement) {
        // Generate a realistic INR/USD rate (around 76)
        const rate = (75.5 + Math.random()).toFixed(2);
        exchangeRateElement.textContent = `₹${rate}`;
    }

    // Import duty
    const importDutyElement = document.getElementById('import-duty');
    if (importDutyElement) {
        importDutyElement.textContent = '7.5%';
    }

    // Market trend
    const marketTrendElement = document.getElementById('market-trend');
    if (marketTrendElement) {
        // Randomly select a trend message
        const trends = [
            'Bullish - Prices expected to rise',
            'Slightly bullish - Moderate price increases expected',
            'Neutral - Prices expected to remain stable',
            'Slightly bearish - Minor price corrections expected',
            'Bearish - Price decreases expected'
        ];
        const randomTrend = trends[Math.floor(Math.random() * trends.length)];
        marketTrendElement.textContent = randomTrend;
    }

    // Global price
    const globalPriceElement = document.getElementById('global-price');
    if (globalPriceElement) {
        // Generate a realistic global gold price (around $1800 per ounce)
        const globalPrice = Math.floor(1780 + Math.random() * 40);
        globalPriceElement.textContent = `$${globalPrice.toLocaleString()} per oz`;
    }
}

// Add CSS for toast messages
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast-message {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        background-color: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 12px 24px;
        border-radius: 30px;
        font-size: 14px;
        z-index: 9999;
        opacity: 0;
        transition: transform 0.3s ease, opacity 0.3s ease;
    }
    
    .toast-message.show {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
`;
document.head.appendChild(toastStyles);

// Add event listener for when the page is fully loaded
window.addEventListener('load', function() {
    // Request notification permission
    if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
        setTimeout(() => {
            Notification.requestPermission();
        }, 3000);
    }

    // Render any existing alerts
    renderAlertsList();

    // Set current year in footer
    const yearElement = document.getElementById('current-year');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // Simulate API call for real gold rates
    // In a real-world scenario, this would call an actual Gold Rate API
    simulateAPICall();
});

// Simulate API call to get real gold rates
function simulateAPICall() {
    // This function simulates an API call that would fetch real gold rates
    // In a production environment, replace this with an actual API call

    // Show loading state
    showToast('Fetching latest gold rates...');

    // Simulate API latency
    setTimeout(() => {
        // In a real implementation, this would be replaced with actual API data
        const goldRateData = {
            price: Math.floor(68500 + Math.random() * 500), // Random price around 68500-69000
            change: Math.floor(Math.random() * 300),
            changePercent: (Math.random() * 0.5).toFixed(2),
            trend: Math.random() > 0.5 ? 'up' : 'down',
            lastUpdated: new Date()
        };

        // Update UI with "real" data
        updateGoldPrice(goldRateData);

        // Update dependent components
        loadGoldRatesByType();
        loadGoldRatesByCities();

        showToast('Gold rates updated successfully');
    }, 1500);
}

// Function to fetch actual gold rates (placeholder for real API implementation)
function fetchActualGoldRates() {
    // This is a placeholder for a real API call
    // You would replace this with an actual API endpoint

    // Example using fetch API:
    /*
    fetch('https://api.example.com/gold-rates')
        .then(response => response.json())
        .then(data => {
            // Process the data
            updateGoldPrice({
                price: data.price,
                change: data.change,
                changePercent: data.changePercent,
                trend: data.change >= 0 ? 'up' : 'down',
                lastUpdated: new Date(data.lastUpdated)
            });

            // Update dependent components
            loadGoldRatesByType();
            loadGoldRatesByCities();
        })
        .catch(error => {
            console.error('Error fetching gold rates:', error);
            showToast('Failed to update gold rates');
        });
    */

    // For this demo, we'll just use our simulation function
    simulateAPICall();
}