/** @odoo-module **/

import { loadBundle, loadJS } from "@web/core/assets";
import { Component, onWillUnmount, useEffect, useRef, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";


class ForecastTemplate extends Component {
    static template = "vex_sync_mercado_libre.forecast";

    setup() {
        this.rpc = useService("rpc");  // Using the RPC service
        this.action = useService("action");  // Using the Action service to open the view

        self = this.action; // Ensure self is set in the constructor

        this.http = useService("http");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notificationService = useService("notification");
        this.state = useState({
            title: "",
            description: "",
            segments: [],
            selectedSegment: null,
            searchText: '',
            filteredProducts: [],
            selectedProduct: null,
            selectedProduct: null,
            column: "",

            showModal: false,

            items: [
            ]
        });

        this.canvasRef = useRef("productosSincronizadosChart");
        this.canvasRef3 = useRef("pie1");
        this.canvasRef4 = useRef("line1");
        this.chart = null;
        this.chart3 = null;
        this.chart4 = null;

        this.products = useState([
            { product_id: 542, product_name: "Cargando...", quantity_sold: 866 },
            { product_id: 424, product_name: "Otros...", quantity_sold: 797 },

        ]);

        this.get_initial_data()

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js")
        });

        onMounted(async () => {
            const instances = await this.orm.searchRead("vex.instance", [
                ["license_valid_str", "=", "active"],
                ["store_type", "=", "mercadolibre"],
            ], ["id"]);
            if (instances.length === 0) {
                this.state.showModal = true;
            } else {
                this.state.showModal = false;
            }
          });

        useEffect(() => {
            const grid = GridStack.init({
                cellHeight: 'auto',
                animate: false, // show immediate (animate: true is nice for user dragging though)
            }).on('change', (ev, gsItems) => {
                this.column = grid.getColumn();
                console.log(this.column)
                console.log("actializado");
            });;

            this.renderChart();
            this.renderChart3();
            this.renderChart4();


            grid.load(this.state.items);

        }, () => []);

        onWillUnmount(() => { this.onWillUnmount() });
    }
    
    redirigirAConfiguracion() {
        this.action.doAction("vex_sync_store.vex_sync_store_open_instances");
    }

    async total_orders_views() {
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        try {
            const result = await this.rpc("/web/action/load", { action_id: "sale.action_orders" })

            const treeView = result.views.find((v) => v[1] === "list");

            this.action.doAction({
                name: 'Sales Orders',
                type: 'ir.actions.act_window',
                res_model: 'sale.order',
                target: 'current',
                domain: [], // Specify your domain if needed
                views: [[treeView[0], 'tree']], // Use the tree view for the order list
            });
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }
    }

    getProductNameById(id) {
        // Directamente accede a this.products (que es el estado)
        const product = this.products.find(product => product.product_id == id);
        return product ? product.product_name : null; // Devuelve el nombre o null si no se encuentra
    }

    async customers_view() {
        this.notificationService.add("Abriendo vista customers", { type: 'warning' });

        try {
            const treeView = result.views.find((v) => v[1] === "list");

            this.action.doAction({
                name: 'Customers',
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                target: 'current',
                domain: [], // Specify your domain if needed
                views: [[false, 'list']], // Use the tree view for the order list
            });

            const respose = await this.rpc("/web/action/load", { action_id: "sale.action_orders" })

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async open_client_view() {
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order


            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
                .then((result) => {  // Change to arrow function to preserve 'this'
                    const treeView = result.views.find((v) => v[1] === "list");
                    console.log(result);
                    // Open view with owl action service
                    this.action.doAction({
                        name: 'Client',
                        type: 'ir.actions.act_window',
                        res_model: 'res.partner',
                        res_id: 888,
                        target: 'new',
                        domain: [], // Specify your domain if needed
                        views: [[false, 'form']], // Use the tree view for the order list
                    });
                })
                .catch((error) => {
                    console.log(error);
                    throw error;
                });

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async open_order_view() {
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order


            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
                .then((result) => {  // Change to arrow function to preserve 'this'
                    const treeView = result.views.find((v) => v[1] === "list");
                    console.log(result);
                    // Open view with owl action service
                    this.action.doAction({
                        name: 'Order',
                        type: 'ir.actions.act_window',
                        res_model: 'sale.order',
                        res_id: 888,
                        target: 'new',
                        domain: [], // Specify your domain if needed
                        views: [[false, 'form']], // Use the tree view for the order list
                    });
                })
                .catch((error) => {
                    console.log(error);
                    throw error;
                });

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async open_product_view() {
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order


            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
                .then((result) => {  // Change to arrow function to preserve 'this'
                    const treeView = result.views.find((v) => v[1] === "list");
                    console.log(result);
                    // Open view with owl action service
                    this.action.doAction({
                        name: 'Product',
                        type: 'ir.actions.act_window',
                        res_model: 'product.template',
                        res_id: 888,
                        target: 'new',
                        domain: [], // Specify your domain if needed
                        views: [[false, 'form']], // Use the tree view for the order list
                    });
                })
                .catch((error) => {
                    console.log(error);
                    throw error;
                });

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async products_view() {
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order


            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
                .then((result) => {  // Change to arrow function to preserve 'this'
                    const treeView = result.views.find((v) => v[1] === "list");
                    console.log(result);
                    // Open view with owl action service
                    this.action.doAction({
                        name: 'Products',
                        type: 'ir.actions.act_window',
                        res_model: 'product.template',
                        target: 'current',
                        domain: [], // Specify your domain if needed
                        views: [[false, 'kanban']],// Use the tree view for the order list
                    });
                })
                .catch((error) => {
                    console.log(error);
                    throw error;
                });

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async questions_view() {
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        // Code
        try {
            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
                .then((result) => {  // Change to arrow function to preserve 'this'
                    const treeView = result.views.find((v) => v[1] === "list");
                    console.log(result);
                    // Open view with owl action service
                    this.action.do_action({
                        name: 'Questions',
                        type: 'ir.actions.act_window',
                        res_model: 'vex.meli.questions',  // Your custom model
                        target: 'current',                // Open in the current window
                        views: [[false, 'tree'], [false, 'form']],  // Use tree or form view
                        domain: [],  // Optional: you can define a filter here if needed
                    });
                })
                .catch((error) => {
                    console.log(error);
                    throw error;
                });

        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }


    addBackground() {
        const actionManagerEl = document.querySelector('.o_action_manager');
        if (actionManagerEl) {
            actionManagerEl.id = 'doodles';
            actionManagerEl.classList.add('list-contact');
        } else {
            console.warn('Elemento .o_action_manager no encontrado.');
        }
    }

    delBackground() {
        const actionManagerEl = document.querySelector('.o_action_manager');
        if (actionManagerEl.id = 'doodles') {
            actionManagerEl.id = null;
            actionManagerEl.classList.remove('list-contact');
        } else {
            console.warn('Elemento .o_action_manager no encontrado.');
        }
    }


    selectSegment(ev) {
        this.state.selectedSegment = this.state.segments.find(segment => segment.id == ev.target.value);
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.canvasRef.el, {
            type: "line",
            data: {
                labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March', 'April', 'May', 'June'],
                datasets: [
                    {
                        label: 'Sales',
                        data: [400, 450, 500, 550, 600, 650, 700, 800, 850, 900, 1000, 1100],
                        fill: false,
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1,
                        pointBackgroundColor: 'rgb(54, 162, 235)',
                    },
                    {
                        label: 'Forecast',
                        data: [null, null, null, null, null, null, null, null, null, null, null, 1100, 1150, 1200, 1250, 1300, 1350, 1400],
                        fill: false,
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5], // Línea punteada
                        tension: 0.1,
                        pointBackgroundColor: 'rgb(255, 99, 132)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {

                    legend: {
                        display: true,
                        position: 'right'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Sales'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        }
                    }
                }
            }
        });
    }

    // Método para manejar el cambio de producto
    onProductChange(event) {
        this.state.selectedProduct = event.target.value;
        console.log("Producto seleccionado:", this.state.selectedProduct);
        const productName = this.getProductNameById(this.state.selectedProduct);
        console.log("Nombre,", productName);

        // Encuentra el input y establece el placeholder al producto seleccionado
        const searchInput = document.getElementById('productSearch'); // Usa document.getElementById en lugar de this.el.querySelector
        searchInput.placeholder = productName
        searchInput.value = '';
        // Oculta la lista de autocompletado
        this.state.filteredProducts = [];

        // Llama a updateChartData para actualizar el gráfico con datos correspondientes
        this.updateChartData();
        let product_id = parseInt(this.state.selectedProduct, 10)


        this.forecast_product(product_id);

    }

    async forecast_product(id_product) {

        let info = await jsonrpc('/web/dataset/call_kw', {
            model: 'product.template',
            method: 'get_product_info',
            args: [id_product],
            kwargs: {}
        });

        console.log("Informacion del producto", info);



        const dates_labels = info.forecast_data.dates.concat(info.forecast_data.forecast_dates)
        this.chart.data.labels = dates_labels || [];

        const length_of_dates_labels = dates_labels.length;
        const sales = info.forecast_data.sales
        console.log(sales);

        const forecasted_sales = info.forecast_data.forecast_sales
        console.log(forecasted_sales);
        const resultArray = new Array(sales.length + forecasted_sales.length).fill(null); // Ajusta la longitud
        if (sales.length > 0) {
            resultArray[resultArray.length - forecasted_sales.length - 1] = sales[sales.length - 1];
        }

        resultArray.splice(resultArray.length - forecasted_sales.length, forecasted_sales.length, ...forecasted_sales);


        this.chart.data.datasets[0].data = sales || [];
        this.chart.data.datasets[1].data = resultArray || [];

        console.log(resultArray);
        console.log(this.chart.data.datasets[1].data, sales.length, length_of_dates_labels
        );

        this.chart.update();




    };



    async get_initial_data() {
        var limit = 20;  // Example limit value
        let topSellingProducts = await jsonrpc('/web/dataset/call_kw', {
            model: 'product.template',
            method: 'get_top_selling_products',
            args: [limit],
            kwargs: {}
        });


        this.products = topSellingProducts
        console.log('Productos más vendidos UPDATED:', this.products);
        this.state.selectedProduct = this.products[0].product_id;
        console.log("Eligiendo el primer valor");

        // Encuentra el input y establece el placeholder al producto seleccionado
        const searchInput = document.getElementById('productSearch'); // Usa document.getElementById en lugar de this.el.querySelector
        const productName = this.getProductNameById(this.products[0].product_id);
        searchInput.placeholder = productName
        searchInput.value = '';

        //const titleElement = document.getElementById('tableTitle');
        // Change the text content of the title element
        //titleElement.textContent = 'Your New Table Name Here';

        this.forecast_product(this.products[0].product_id);

        this.calculateTableData();


    }

    async calculateTableData() {
        console.log("this.products");
        let table_data = await jsonrpc('/web/dataset/call_kw', {
            model: 'product.template',
            method: 'calculate_table_data',
            args: [this.products],
            kwargs: {}
        });
        this.products = table_data;
        console.log("Datos tabla procesados", table_data);
        this.render()


    }

    async updateChartData() {



        console.log("Actual", this.products);

        const productData = {
            product1: [500, 600, 800, 1200, 1500, 1800, 1600, 1400, 1700, 2000, 2200, 2400], // Ventas históricas para producto 1
            product2: [400, 550, 700, 950, 1200, 1500, 1300, 1100, 1400, 1600, 1900, 2100], // Ventas históricas para producto 2
            product3: [300, 400, 500, 600, 800, 1000, 1100, 1300, 1200, 1400, 1600, 1800], // Ventas históricas para producto 3
        };

        const forecastData = {
            product1: [null, null, null, null, null, null, null, null, null, null, null, 2400, 2500, 2600, 2700, 2800, 2900, 3000], // Pronóstico para producto 1
            product2: [null, null, null, null, null, null, null, null, null, null, null, 2100, 2200, 2300, 2400, 2500, 2600, 2700], // Pronóstico para producto 2
            product3: [null, null, null, null, null, null, null, null, null, null, null, 1800, 1900, 2000, 2100, 2200, 2300, 2400], // Pronóstico para producto 3
        };

        // Actualiza las ventas históricas y pronósticos del producto seleccionado
        this.chart.data.datasets[0].data = productData[this.state.selectedProduct] || [];
        this.chart.data.datasets[1].data = forecastData[this.state.selectedProduct] || [];
        this.chart.update();





        //this.products = topSellingProducts



    }

    onSearchInput(ev) {
        const searchText = ev.target.value.toLowerCase();
        this.state.filteredProducts = this.products.filter(product =>
            product.product_name.toLowerCase().includes(searchText)
        );
    }




    clearSelection() {
        this.state.selectedProduct = null;
        this.state.searchText = '';
        this.state.filteredProducts = [];
        console.log("Seleccion limpiada");
    }

    mounted() {
        this.renderChart();
    }






    renderChart2() {
        if (this.chart2) {
            this.chart2.destroy();
        }

        this.chart2 = new Chart(this.canvasRef2.el, {
            type: "line",
            data: {
                labels: ['January', 'February', 'March', 'April'],
                datasets: [
                    {
                        label: 'Organic',
                        data: [50, 60, 70, 80],
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Paid',
                        data: [50, 53, 40, 60],
                        backgroundColor: 'rgba(144, 238, 144, 0.5)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }

                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Sales Evolution', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: {
                            display: true,
                            color: "rgba(255,99,132,0.2)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderChart3() {
        if (this.chart3) {
            this.chart3.destroy();
        }

        this.chart3 = new Chart(this.canvasRef3.el, {
            type: "line", // Cambiado a 'line' para gráfico de línea
            data: {
                labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'],
                datasets: [
                    {
                        label: 'Orders',
                        data: [150, 165, 160, 190, 180, 210, 205, 225, 215, 240, 260, 275, null, null, null], // Datos históricos con mayor volatilidad
                        fill: false,
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.2,
                        pointBackgroundColor: 'rgb(54, 162, 235)',
                    },
                    {
                        label: 'Forecast',
                        data: [null, null, null, null, null, null, null, null, null, null, null, 275, 290, 315, 330], // Previsión con oscilaciones más marcadas
                        fill: false,
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5], // Línea punteada para indicar forecast
                        tension: 0.2,
                        pointBackgroundColor: 'rgb(255, 99, 132)',
                    }
                ]

            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Order Forecast',
                        font: {
                            size: 24
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                let label = tooltipItem.label || '';
                                let value = tooltipItem.raw || 0;
                                return `${label}: ${value} orders`;
                            }
                        }
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Orders'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        }
                    }
                }
            }
        });
    }



    renderChart4() {
        if (this.chart4) {
            this.chart4.destroy();
        }

        this.chart4 = new Chart(this.canvasRef4.el, {
            type: "line",
            data: {
                labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March', 'April', 'May', 'June'],
                datasets: [
                    {
                        label: 'New Clients',
                        data: [35, 40, 45, 50, 60, 65, 70, 75, 80, 85, 90, 95, null, null, null, null, null, null],
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        pointBackgroundColor: 'rgb(75, 192, 192)',
                        fill: false,
                    },
                    {
                        label: 'Forecast',
                        data: [null, null, null, null, null, null, null, null, null, null, null, 95, 100, 105, 110, 115, 120, 125],
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5], // Línea punteada para el forecast
                        tension: 0.1,
                        pointBackgroundColor: 'rgb(255, 99, 132)',
                        fill: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Clients Forecast',
                        font: {
                            size: 24
                        }
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Users'
                        },
                        stacked: false,
                        grid: {
                            display: true,
                            color: "rgba(255, 99, 132, 0.2)"
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }


    renderChart5() {
        if (this.chart5) {
            this.chart5.destroy();
        }

        this.chart5 = new Chart(this.canvasRef5.el, {
            type: "line",
            data: {
                labels: ['January', 'February', 'March', 'April'],
                datasets: [
                    {
                        label: 'Changes',
                        data: [50, 60, 70, 80],
                        backgroundColor: 'rgba(75, 92, 292, 0.4)',
                        borderColor: 'rgba(75, 92, 292, 0.4)',
                        tension: 0.1
                    },
                    {
                        label: 'Returns',
                        data: [50, 53, 40, 60],
                        backgroundColor: 'rgba(120, 38, 144, 0.5)',
                        borderColor: 'rgba(120, 38, 144, 0.5)',
                        tension: 0.1
                    }

                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Exchanges And Returns', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: {
                            display: true,
                            color: "rgba(255,99,132,0.2)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderChart6() {
        if (this.chart6) {
            this.chart6.destroy();
        }

        this.chart6 = new Chart(this.canvasRef6.el, {
            type: "bar",
            data: {
                labels: ['Proteins', 'Vitamins', 'Amino Acids', 'Pre-Workouts', 'Post-Workouts', 'Fat Burners'],
                datasets: [
                    {
                        label: 'History',
                        data: [15, 35, 55, 75, 52, 33],
                        backgroundColor: 'rgba(248, 186, 215, 0.6)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },

                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Top products', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: {
                            display: true,
                            color: "rgba(255,99,132,0.2)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderChart7() {
        if (this.chart7) {
            this.chart7.destroy();
        }
        this.chart7 = new Chart(this.canvasRef7.el, {

            type: "bar",
            data: {
                labels: ['January', 'February', 'March', 'April'],
                datasets: [
                    {
                        label: 'Total Sale - Commissions, shipping and Ads',
                        data: [20, 40, 60, 80],
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },

                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Top Clients', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: {
                            display: true,
                            color: "rgba(255,99,132,0.2)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }

        });
    }

    renderChart8() {
        if (this.chart8) {
            this.chart8.destroy();
        }

        this.chart8 = new Chart(this.canvasRef8.el, {
            type: "bar",
            data: {
                labels: ['Decorations', 'Exteriors', 'Gardens', 'Botany', 'Sports', 'Authentic'],
                datasets: [
                    {
                        label: 'History',
                        data: [15, 35, 55, 75, 52, 73],
                        backgroundColor: 'rgba(248, 186, 215, 0.6)',
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },

                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Questions', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: {
                            display: true,
                            color: "rgba(255,99,132,0.2)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    renderChart9() {
        if (this.chart9) {
            this.chart9.destroy();
        }

        this.chart9 = new Chart(this.canvasRef9.el, {
            type: "line",
            data: {
                labels: ['January', 'February', 'March', 'April', 'May',],
                datasets: [{
                    label: 'Sales evolution',
                    data: [5000, 6000, 7000, 8000, 5600, 5000],
                    fill: false,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Average Customer Order', // Título principal
                        font: {
                            size: 24 // Tamaño del texto del título
                        }
                    },
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    onWillUnmount() {
        if (this.chart) {
            this.chart.destroy();
        }

    }


}

registry.category("actions").add("vex_sync_mercado_libre.forecast", ForecastTemplate);


