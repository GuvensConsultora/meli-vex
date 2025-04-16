from odoo import api, fields, models
import requests
import logging
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from odoo.exceptions import UserError
from PyPDF2 import PdfMerger
import io

API_URI = 'https://api.mercadolibre.com'
PRINT_TICKET_URI = f"{API_URI}/shipment_labels?shipment_ids={{}}&response_type=pdf"

_logger = logging.getLogger(__name__)


class VexSaleOrder(models.Model):
    _inherit = "sale.order"

    # Fields
    meli_code = fields.Char('Código ML')
    server_meli = fields.Boolean('server_meli')
    shipping_id = fields.Char('Shipment ID')
    shipping_type = fields.Char('Shipment Type')
    shipping_name = fields.Char(
        'Shipment Name',
        compute="get_shipment_name",
        help="Mercado Envíos(drop_off): El vendedor imprime la etiqueta y realiza el envío en el Correo.\n"
             "Places(xd_drop_off) \nColeta(cross_docking)\nFlex(self_service) \nFull(fullfilment)"
    )
    shipping_status = fields.Char('Shipment Status')
    meli_order_comment = fields.Char('Comment')
    fulfilled = fields.Boolean('Fulfilled')
    buying_mode = fields.Char('Buying Mode')
    listing_type_id = fields.Char('Listing Type')
    pack_id = fields.Char('Pack ID')
    payment_method_id = fields.Char('Payment Method ID')
    operation_type = fields.Char('Operation Type')
    payment_type = fields.Char('Payment Type')
    payment_status = fields.Char('Payment Status')
    payment_status_detail = fields.Char('Payment Status Detail')
    total_paid_amount = fields.Float('Total Paid Amount')
    marketplace_fee = fields.Float('Marketplace Fee')
    shipping_cost = fields.Float('Shipping Cost')
    meli_payment_code = fields.Char('Payment ID')
    meli_collector_id = fields.Char('Collector ID')
    meli_card_id = fields.Char('Card ID')
    product_sold_ids = fields.Many2many(
        'product.template',
        string='Sold Products',
        compute="get_product_sold"
    )
    shipment_label = fields.Binary('Shipment Label', readonly=True)
    instance_id = fields.Many2one('vex.instance', string='Instance')
    net_profit = fields.Float(string="Net Profit", compute="_compute_net_profit", store=True)
    tags = fields.Char('Tags')
    order_status = fields.Char('VEX Order Status')
    order_is_closed = fields.Boolean('Order is Closed?')

    meli_channel = fields.Char('Channel of sale')
    meli_flows = fields.Json(string="Flows", help="Stores the JSON representation of the flows.")

    store_type = fields.Selection([
        ('mercadolibre', 'Mercado Libre'),
        ('walmart', 'Walmart')
    ], string="Store Type", required=True, default='mercadolibre')

    in_mediation = fields.Boolean('Order is in mediation?', default = False)
    expected_resolution = fields.Boolean('Expected Resolution?', default = False)
    mediation_solved = fields.Boolean('Mediation Solved?', default = False)
    #waiting_ml_mediation = fields.Boolean('Mediation Solved?', default = False)
    waiting_ml_intervention = fields.Boolean('Waiting ML Intervention?', default = False)


    @api.model
    def button_process_shipping_label(self, data):
        # Primero, muestra la notificación
        

        notification_action_error = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error',
                'message': 'La orden no es compatible con la generación de etiquetas de envío. (FULL, FLEX, etc.)',
                'sticky': False,  # El mensaje desaparece automáticamente
            },
        }
        
        # Luego, ejecuta tu lógica personalizada
        shipping_id = self.env.context.get('shipping_id')
        meli_code = self.env.context.get('meli_code')

        context_values = dict(self.env.context)  # Convierte el contexto a un diccionario
        _logger.info(f"[INFO] Valores del contexto: {context_values}")

        

        acces_token = self.env['sale.order'].search([('meli_code', '=', meli_code)], limit=1).instance_id.access_token

        if acces_token and shipping_id:
            pdf_url = self.get_shipping_label_content(shipping_id, acces_token)

            if pdf_url:
                # Codifica el contenido binario del PDF en Base64
                encoded_pdf = base64.b64encode(pdf_url).decode('utf-8')

                # Guarda el contenido en ir.config_parameter
                self.env['ir.config_parameter'].sudo().set_param('current_shipping_label', encoded_pdf)

                # Redirige al controlador
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/custom/view_pdf_label',
                    'target': 'new',
                }

        if not pdf_url:
            return notification_action_error
    

    @api.model
    def process_label(self, shipping_id, meli_code):    
        acces_token = self.env['sale.order'].search([('meli_code', '=', meli_code)], limit=1).instance_id.access_token

        if acces_token and shipping_id:
            pdf_url = self.get_shipping_label_content(shipping_id, acces_token)

            if pdf_url:
                # Devuelve el contenido binario del PDF
                return pdf_url
        return None

    def _process_shipping_logic(self, data):
        # Aquí ejecutas la lógica personalizada que necesitas
        # Por ejemplo, generar la guía de envío
        # (Puedes conectar con una API, generar un documento, etc.)
        _logger.info("Ejecutando lógica de procesamiento de la guía de envío...")

    @api.model
    def button_mediation(self,values):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Información',
                'message': 'Estamos a la espera de que el usuario responda a la mediación.',
                'sticky': False,  # El mensaje desaparece automáticamente
            },
        }
    
    @api.model
    def button_mediation_solved(self,values):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Información',
                'message': 'Esta orden pertenece a una mediación que ya ha sido resuelta.',
                'sticky': False,  # El mensaje desaparece automáticamente
            },
        }

    def button_ml_intervention(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Información',
                'message': 'Mercado Libre está interviniendo en la reclamación y estamos a la espera de una respuesta.',
                'sticky': False,  # El mensaje desaparece automáticamente
            },
        }

    @api.model
    def action_raise_error(self,values):

        resource_id = self.env.context.get('resource_id')

        record = self.env['vex.soluciones.mercadolibre.claim'].search([('resource_id', '=', resource_id)], limit=1)
        if not record:
            raise UserError(f"No se encontró un registro con resource = {resource_id}")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vex.soluciones.mercadolibre.claim',
            'view_mode': 'form',
            'target': 'new',
            'res_id': record.id,  # Abrir el registro específico
            'name': 'Mediation Menu',
        }
        

    # Methods
    def get_shipment_name(self):
        for item in self:
            shipping_types = {
                'drop_off': 'Mercado Envíos',
                'xd_drop_off': 'Places',
                'cross_docking': 'Coleta',
                'self_service': 'Flex',
                'fulfillment': 'Full'
            }
            item.shipping_name = shipping_types.get(item.shipping_type, '')

    def get_product_sold(self):
        for item in self:
            item.product_sold_ids = [line.product_template_id.id for line in item.order_line]

    def get_shipping_label_content(self, shipment_id: str, access_token: str):
        """Obtiene el contenido del PDF para un shipment_id específico."""
        _logger.info(f"[START] Obteniendo la etiqueta de envío para el shipment_id {shipment_id}")

        url = f"https://api.mercadolibre.com/shipment_labels?shipment_ids={shipment_id}&savePdf=Y"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        _logger.info(f"[INFO] URL: {url}")
        _logger.info(f"[INFO] Headers: {headers}")

        try:
            response = requests.get(url, headers=headers)
            _logger.info(f"[SUCCESS] Solicitud enviada. Código de estado: {response.status_code}")
            response.raise_for_status()


            if response.status_code == 200:
                _logger.info("[SUCCESS] Etiqueta de envío obtenida con éxito.")
                return response.content  # Devuelve el contenido binario del PDF
            else:
                _logger.warning(f"[WARNING] Respuesta inesperada: {response.status_code}")
                return None
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al obtener la etiqueta de envío: {str(e)}")
            return None

    def print_guides(self):
        """Acción personalizada que se ejecutará desde el menú."""
        pdfs = []

        for order in self:
            _logger.info(f"Procesando la orden {order.name}...")
            pdf_binary = self.process_label(order.shipping_id, order.meli_code)
            if pdf_binary:
                pdfs.append(pdf_binary)

        if pdfs:
            # Combina todos los PDFs en uno solo
            combined_pdf = self.combine_pdfs(pdfs)

            # Guarda el PDF combinado en ir.config_parameter
            encoded_combined_pdf = base64.b64encode(combined_pdf).decode('utf-8')
            self.env['ir.config_parameter'].sudo().set_param('current_shipping_label', encoded_combined_pdf)

            # Redirige al usuario al controlador para descargar el PDF combinado
            return {
                'type': 'ir.actions.act_url',
                'url': '/custom/view_pdf_label',
                'target': 'new',
            }
        else:
            # Notifica al usuario si no se pudieron generar etiquetas
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No se pudieron generar las etiquetas de envío.',
                    'sticky': False,
                },
            }

    def combine_pdfs(self, pdf_binaries):
        """Combina múltiples PDFs en uno solo."""
        merger = PdfMerger()
        for pdf_binary in pdf_binaries:
            pdf_stream = io.BytesIO(pdf_binary)
            merger.append(pdf_stream)

        output_stream = io.BytesIO()
        merger.write(output_stream)
        merger.close()

        return output_stream.getvalue()


    @api.depends('order_line', 'marketplace_fee', 'shipping_cost', 'order_status')
    def _compute_net_profit(self):
        for order in self:
            # Procesar solo órdenes con estado "Completada"
            if order.order_status == "Completada":
                total_sales = order.amount_total
                total_cost = sum(
                    line.product_id.standard_price * line.product_uom_qty
                    for line in order.order_line
                )
                # Validar que todos los productos tengan un standard_price > 0
                if all(line.product_id.standard_price > 0 for line in order.order_line):
                    order.net_profit = total_sales - (total_cost + order.marketplace_fee + order.shipping_cost)
                else:
                    # Si algún producto tiene un precio estándar <= 0, el beneficio es 0
                    order.net_profit = 0.0
            else:
                # Si la orden no está completada, el beneficio es 0
                order.net_profit = 0.0

    def print_ticket(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {self.instance_id.access_token}'
        }
        response = requests.get(PRINT_TICKET_URI.format(self.shipping_id), headers=headers)
        if response.status_code == 200:
            self.shipment_label = base64.b64encode(response.content)
        return response.content

    # Dashboard Methods
    @api.model
    def orders_synced_today(self):
        today = datetime.today().date()
        current_user = self.env.user 
        return self.search_count([
            ('date_order', '>=', today),
            ('date_order', '<', today + timedelta(days=1)),
            ('store_type', '=', 'mercadolibre'),
            ('instance_id', '=', current_user.meli_instance_id.id),
        ])

    @api.model
    def get_top_clients_all_time(self):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "top_clients_all_time"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            # Obtener órdenes confirmadas
            orders = self.search([
                ('state', '=', 'sale'),
                ('store_type', '=', 'mercadolibre'),  # Filtrar por store_type = 'walmart'
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])
            client_data = {}

            for order in orders:
                client = order.partner_id
                if client.id not in client_data:
                    client_data[client.id] = {
                        'name': client.name,
                        'purchases': 0,
                        'volume': 0.0
                    }
                client_data[client.id]['purchases'] += 1
                client_data[client.id]['volume'] += order.amount_total

            # Ordenar clientes por volumen de compras y número de compras
            top_clients = sorted(
                client_data.values(),
                key=lambda x: (-x['volume'], -x['purchases'])
            )[:10]

            # **Formatear el campo `volume` como moneda**
            def format_currency(value):
                return "${:,.2f}".format(value)

            for client in top_clients:
                client['volume'] = format_currency(client['volume'])

            # Crear o actualizar registro
            record_data = {
                'month': 'All Time',
                'year': 0,
                'new_customers': 0,
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': top_clients,
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return top_clients

        return record.extra_data if 'extra_data' in record else []
            
    @api.model
    def get_latest_orders(self):
        # Buscar las últimas 10 órdenes confirmadas
        current_user = self.env.user 
        orders = self.search([
            ('state', '=', 'sale'),
            ('store_type', '=', 'mercadolibre'),  # Filtrar por store_type = 'mercadolibre'
            ('instance_id', '=', current_user.meli_instance_id.id)
        ], order='date_order desc', limit=10)
        result = []

        # Función para formatear dinero
        def format_currency(value):
            return "${:,.2f}".format(value)

        for order in orders:
            for line in order.order_line:
                product_name = line.product_id.name
                # Recortar el nombre del producto si excede 20 caracteres
                if len(product_name) > 20:
                    product_name = product_name[:20] + "..."

                result.append({
                    'client_name': order.partner_id.name or "N/A",
                    'order_number': order.name,
                    'product_name': product_name,
                    'quantity': line.product_uom_qty,
                    'phone': order.partner_id.phone or "N/A",
                    'email': order.partner_id.email or "N/A",
                    # Formatear el campo amount_total
                    'amount_total': format_currency(order.amount_total),
                })

        return result


    @api.model
    def get_top_products_all_time(self):
        _logger.info("Iniciando el método get_top_products_all_time.")

        DashboardData = self.env['vex.dashboard.data']
        data_for = "top_products_all_time"
        current_user = self.env.user 

        # Buscar registro existente en el modelo de datos del dashboard
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        _logger.info(f"Registro encontrado en DashboardData: {record}")

        # Validar si el registro es None o está desactualizado
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            _logger.info("No se encontró registro válido o está desactualizado.")
            
            # Obtener órdenes confirmadas
            orders = self.search([
                ('state', '=', 'sale'),
                ('store_type', '=', 'mercadolibre'),  # Filtrar por store_type = 'mercadolibre'
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])
            _logger.info(f"Órdenes encontradas: {len(orders)}")

            product_data = {}

            # Iterar sobre las líneas de pedido
            for order in orders:
                for line in order.order_line:
                    product = line.product_id
                    if product.id not in product_data:
                        product_data[product.id] = {
                            'name': product.name,
                            'quantity_sold': 0.0,
                            'sales_volume': 0.0
                        }
                    product_data[product.id]['quantity_sold'] += line.product_uom_qty
                    product_data[product.id]['sales_volume'] += line.price_subtotal

            #_logger.info(f"Datos del producto procesados: {product_data}")

            # Ordenar productos por volumen de ventas y cantidad vendida
            top_products = sorted(
                product_data.values(),
                key=lambda x: (-x['sales_volume'], -x['quantity_sold'])
            )[:10]
            _logger.info(f"Top productos calculados: {top_products}")

            # **Formatear datos**
            def format_number(value):
                return "{:,.0f}".format(value)  # Formatear con separadores de miles y sin decimales

            def format_currency(value):
                return "${:,.2f}".format(value)  # Formatear con símbolo de moneda, 2 decimales

            for product in top_products:
                product['quantity_sold'] = format_number(product['quantity_sold'])
                product['sales_volume'] = format_currency(product['sales_volume'])

            _logger.info(f"Top productos formateados: {top_products}")

            # Crear o actualizar el registro en el dashboard
            record_data = {
                'month': 'All Time',
                'year': 0,
                'new_customers': 0,
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': top_products,
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
                _logger.info(f"Registro existente actualizado con éxito: {record}")
            else:
                record = DashboardData.create(record_data)
                _logger.info(f"Nuevo registro creado: {record}")
            
            return top_products

        # Retornar los datos calculados
        result = record.extra_data if 'extra_data' in record else []
        _logger.info(f"Resultado final retornado: {result}")

        return result

    @api.model
    def get_total_orders_count(self):
        current_user = self.env.user 
        return self.search_count([
            ('store_type', '=', 'mercadolibre'),
            ('instance_id', '=', current_user.meli_instance_id.id),
        ])
    
    @api.model
    def total_ventas_mercadolibre(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1)) - relativedelta(days=1)

        orders = self.search([
            ('store_type', '=', 'mercadolibre'),
            ('date_order', '>=', first_day),
            ('date_order', '<=', last_day)
        ])

        total_sales = sum(orders.mapped('amount_total'))

        currency = orders[:1].currency_id  # Toma la moneda del primer pedido
        currency_symbol = currency.symbol if currency else '$'
        return {
            'total_sales': round(total_sales, 2),
            'currency_symbol': currency_symbol
        }

    @api.model
    def mes_pasado_ventas_mercadolibre(self):
        today = fields.Date.today()
        first_day_current_month = today.replace(day=1)
        first_day_last_month = first_day_current_month - relativedelta(months=1)
        last_day_last_month = first_day_current_month - relativedelta(days=1)

        orders = self.search([
            ('store_type', '=', 'mercadolibre'),
            ('date_order', '>=', first_day_last_month),
            ('date_order', '<=', last_day_last_month)
        ])

        total_sales = sum(orders.mapped('amount_total'))

        return {
            'total_sales': round(total_sales, 2)
        }
    
    @api.model
    def get_new_customers_last_month(self):
        current_user = self.env.user 
        last_month = datetime.today().date() - timedelta(days=30)
        return self.env['res.partner'].search_count([('create_date', '>=', last_month),('instance_id', '=', current_user.meli_instance_id.id)])

    @api.model
    def get_new_customers_first_purchase_this_month(self):
        today = datetime.today().date()
        first_of_month = today.replace(day=1)
        DashboardData = self.env['vex.dashboard.data']
        data_for = "new_customers_first_purchase"
        current_user = self.env.user 

        record = DashboardData.search([
            ('month', '=', first_of_month.strftime('%B')),
            ('year', '=', first_of_month.year),
            ('data_for', '=', data_for),
            ('instance_id', '=', current_user.meli_instance_id.id)
        ], limit=1, order='last_updated desc')

        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            orders = self.search([
                ('date_order', '>=', first_of_month),
                ('state', '=', 'sale'),
                ('store_type', '=', 'mercadolibre'),
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])
            new_customers = {
                order.partner_id.id for order in orders
                if self.search_count([('partner_id', '=', order.partner_id.id), ('state', '=', 'sale'), ('instance_id', '=', current_user.meli_instance_id.id)]) == 1
            }
            record_data = {
                'month': first_of_month.strftime('%B'),
                'year': first_of_month.year,
                'new_customers': len(new_customers),
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return len(new_customers)

        return record.new_customers

    @api.model
    def count_customers_with_server_meli(self):
        current_user = self.env.user 
        return self.env['res.partner'].search_count([('server_meli', '=', True),('instance_id', '=', current_user.meli_instance_id.id)])

    @api.model
    def get_total_products(self):
        current_user = self.env.user 
        return self.env['product.template'].search_count([
            ('store_type', '=', 'mercadolibre'),('instance_id', '=', current_user.meli_instance_id.id)
        ])

    @api.model
    def get_or_update_new_customers_data(self): #chart customers, moth by month  CUSTOMERS EVOLUTION
        DashboardData = self.env['vex.dashboard.data']
        data_for = "new_customers_chart"
        current_user = self.env.user 
        
        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            today = datetime.today().date()
            data_series = []

            for i in range(6):
                first_of_month = (today - relativedelta(months=i)).replace(day=1)
                last_of_month = first_of_month + relativedelta(months=1) - timedelta(days=1)
                
                # Obtener las órdenes confirmadas del mes
                orders = self.search([
                    ('date_order', '>=', first_of_month),
                    ('date_order', '<=', last_of_month),
                    ('state', '=', 'sale'),
                    ('store_type', '=', 'mercadolibre'),
                    ('instance_id', '=', current_user.meli_instance_id.id)
                ])
                
                # Identificar nuevos clientes
                new_customers = {
                    order.partner_id.id for order in orders
                    if self.search_count([('partner_id', '=', order.partner_id.id), ('state', '=', 'sale'),('instance_id', '=', current_user.meli_instance_id.id)]) == 1
                }
                
                data_series.append({
                    'month': first_of_month.strftime('%B'),
                    'year': first_of_month.year,
                    'new_customers': len(new_customers),
                })

            # Actualizar o crear registro con datos en formato JSON
            record_data = {
                'month': 'Multiple',  # Representa múltiples meses
                'year': 0,  # No es específico de un año
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': data_series,  # Guardar todos los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return data_series

        return record.extra_data if 'extra_data' in record else []

    @api.model
    def get_monthly_profit_last_6_months(self):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "monthly_profit_last_6_months"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or (record.last_updated and record.last_updated < fields.Datetime.now() - timedelta(days=1)):
            today = fields.Date.today()
            six_months_ago = today - relativedelta(months=6)
            monthly_profit = {}

            # Obtener órdenes confirmadas de los últimos 6 meses
            orders = self.search([
                ('date_order', '>=', six_months_ago),
                ('date_order', '<=', today),
                ('state', '=', 'sale'),
                ('store_type', '=', 'mercadolibre'),
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])
            _logger.info(f"Orders found: {len(orders)}")

            for order in orders:
                if not order.date_order:
                    continue

                # Convertir `date_order` a fecha pura y extraer el mes y año
                order_date = fields.Date.to_date(order.date_order)  # Convierte a solo fecha (YYYY-MM-DD)
                month_year = order_date.strftime('%Y-%m')  # Extrae año y mes como string
              
              
                # Sumar el total de las órdenes
                order_total = sum(line.price_total for line in order.order_line)
                monthly_profit[month_year] = monthly_profit.get(month_year, 0) + order_total
            
         
            # Formatear los resultados como una lista ordenada de diccionarios
            data_series = [
                {'month_year': key, 'profit': round(value, 2)}
                for key, value in sorted(monthly_profit.items())
            ]

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'Multiple',  # Representa múltiples meses
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': data_series,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                record = DashboardData.create(record_data)


            return data_series

        return record.extra_data if record else []

    @api.model
    def get_average_custom_order_last_6_months(self):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "average_custom_order_last_6_months"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            today = datetime.today().date()
            six_months_ago = today - relativedelta(months=6)
            average_custom_order = {}

            # Obtener órdenes confirmadas de los últimos 6 meses
            orders = self.search([
                ('date_order', '>=', six_months_ago),
                ('state', '=', 'sale'),
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])

            # Agrupar datos por mes y calcular el promedio
            monthly_data = {}
            for order in orders:
                month_year = order.date_order.strftime('%Y-%m')
                if month_year not in monthly_data:
                    monthly_data[month_year] = {'total_amount': 0, 'unique_customers': set()}

                # Sumar el total de la orden
                monthly_data[month_year]['total_amount'] += order.amount_total

                # Agregar el cliente a la lista de clientes únicos
                monthly_data[month_year]['unique_customers'].add(order.partner_id.id)
                

            # Calcular el promedio de cada mes
            data_series = []
            for month_year, data in sorted(monthly_data.items()):
                unique_customers_count = len(data['unique_customers'])
                average_order = round(data['total_amount'] / unique_customers_count, 2) if unique_customers_count > 0 else 0
                data_series.append({
                    'month_year': month_year,
                    'average_order': average_order
                })

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'Multiple',  # Representa múltiples meses
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': data_series,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return data_series

        # Retornar los datos desde el campo `extra_data`
        return record.extra_data if 'extra_data' in record else []
    
    @api.model
    def get_top_categories(self):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "top_categories"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            # Obtener líneas de pedidos confirmados
            sale_lines = self.env['sale.order.line'].search([
                ('order_id.state', 'in', ['sale', 'done'])  # Solo órdenes confirmadas o finalizadas
            ])

            # Si no hay líneas de pedido, retornar un array vacío
            if not sale_lines:
                return []

            # Agrupar ventas por categoría
            category_sales = {}
            for line in sale_lines:
                category = line.product_id.categ_id
                instance = line.product_id.categ_id.instance_id.id
                if category and instance==current_user.meli_instance_id.id:
                    category_sales[category] = category_sales.get(category, 0) + line.price_subtotal

            # Calcular total de ventas
            total_sales = sum(category_sales.values())

            # Si no hay ventas totales, retornar un array vacío
            if total_sales == 0:
                return []

            # Calcular porcentaje por categoría
            category_percentage = [
                {
                    'category': category.name,
                    'sales': sales,
                    'percentage': (sales / total_sales) * 100
                }
                for category, sales in category_sales.items()
            ]

            # Ordenar por porcentaje descendente y tomar las 5 primeras
            top_categories = sorted(category_percentage, key=lambda x: x['percentage'], reverse=True)[:5]

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'Multiple',  # Representa múltiples periodos
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': top_categories,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            # Retornar los datos calculados
            return top_categories

        # Retornar los datos desde el campo `extra_data`
        return record.extra_data if 'extra_data' in record else []

    @api.model
    def get_monthly_order_status_counts_last_4_months(self):
        """
        Calcula las órdenes completadas y canceladas agrupadas por mes en los últimos 4 meses.
        Los datos se almacenan o actualizan en la base de datos.
        """
        DashboardData = self.env['vex.dashboard.data']
        data_for = "monthly_order_status_counts_last_4_months"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            # Obtener fecha actual y calcular fecha hace 4 meses
            today = datetime.today().date()
            four_months_ago = today - relativedelta(months=4)

            # Filtrar órdenes en el rango de tiempo
            orders = self.search([
                ('date_order', '>=', four_months_ago),
                ('order_status', 'in', ['Completada', 'Canceled']),
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])

            # Inicializar estructura para los datos
            monthly_status_counts = {}

            # Recorrer las órdenes y agrupar por mes y estado
            for order in orders:
                month_year = order.date_order.strftime('%Y-%m')  # Formato: '2024-11'
                if month_year not in monthly_status_counts:
                    monthly_status_counts[month_year] = {'Completada': 0, 'Canceled': 0}
                if order.order_status in monthly_status_counts[month_year]:
                    monthly_status_counts[month_year][order.order_status] += 1

            # Convertir los resultados a una lista de diccionarios
            data_series = [
                {
                    'month_year': month,
                    'completadas': data['Completada'],
                    'canceladas': data['Canceled']
                }
                for month, data in sorted(monthly_status_counts.items())
            ]

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'Multiple',  # Representa múltiples meses
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': data_series,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return data_series

        # Retornar los datos desde el campo `extra_data`
        return record.extra_data if 'extra_data' in record else []
    
    @api.model
    def get_sales_by_channel_last_5_months(self):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "sales_by_channel_last_5_months"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1, order='last_updated desc')
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            today = datetime.today().date()
            five_months_ago = today - relativedelta(months=5)

            # Obtener órdenes confirmadas de los últimos 5 meses
            orders = self.search([
                ('date_order', '>=', five_months_ago),
                ('state', '=', 'sale'),
                ('instance_id', '=', current_user.meli_instance_id.id)
            ])

            # Agrupar datos por mes y canal
            monthly_data = {}
            for order in orders:
                month_year = order.date_order.strftime('%Y-%m')
                if month_year not in monthly_data:
                    monthly_data[month_year] = {'supermarket': 0, 'catalog': 0}

                # Analizar el campo `tags` para clasificar las ventas
                tags = order.tags or ''
                if 'supermarket' in tags:
                    monthly_data[month_year]['supermarket'] += 1
                if 'catalog' in tags:
                    monthly_data[month_year]['catalog'] += 1

            # Formatear los datos para el gráfico
            data_series = []
            for month_year, data in sorted(monthly_data.items()):
                data_series.append({
                    'month_year': month_year,
                    'supermarket': data['supermarket'],
                    'catalog': data['catalog']
                })

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'Multiple',  # Representa múltiples meses
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': data_series,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return data_series

        # Retornar los datos desde el campo `extra_data`
        return record.extra_data if 'extra_data' in record else []

