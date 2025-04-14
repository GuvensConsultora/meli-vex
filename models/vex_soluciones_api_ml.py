import requests
import json
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import models, fields, api
from io import BytesIO
from PIL import Image
import re,random
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

GET_ORDER="https://api.mercadolibre.com/orders/search?seller={}&order.date_created.from={}&order.date_created.to={}&sort=date_desc&limit={}&offset={}"
ME_URI="https://api.mercadolibre.com/users/me"
MERCADO_LIBRE_URL = 'https://api.mercadolibre.com'

RUT_URI="https://api.mercadolibre.com/orders/{}/billing_info"

class MercadoLibreProduct(models.Model):
    _name = 'mercado.libre.product'

    name = fields.Char("Name", compute="_compute_name", store=True)
    price = fields.Float("Price")
    product_url = fields.Char("Product URL")
    image = fields.Image("Product Image")  # Campo de 
    
    product = fields.Many2one('product.template', string='Producto')
    product_id = fields.Many2one('product.template', string="Product", ondelete="cascade")
    product_image = fields.Binary("Imagen del Producto", compute="_compute_product_image", store=True)
    link = fields.Text("Link de Mercado Libre")
    competence_image =  fields.Binary("IMG", store=True)
    precio_comparacion = fields.Selection([
        ('cheapest', 'Compare with the cheapest publication in the group'),
        ('most_expensive', 'Compare to the most expensive publication in the group'),
        ('average', 'Compare with the average price of the group')
    ], string="Tipo de comparación de precio", default="average")
    precio_opcion = fields.Selection([
        ('porcentaje', 'Use a percentage value'),
        ('valor_fijo', 'Use a flat value')
    ], string="Tipo de opciones de precio", default='valor_fijo')
    ganancia_opcion = fields.Selection([
        ('porcentaje', 'Use a percentage gain value'),
        ('valor_fijo', 'Use a flat gain value')
    ], string="Tipo de opciones de precio", default='valor_fijo')
    barato_caro = fields.Selection([
        ('barato', 'Cheaper'),
        ('caro', 'More expensive')
    ], string="Tipo de valor", default="barato" )

    precio_min = fields.Monetary("Minimum Price", digits=(16, 2), default="0.00", currency_field='currency_id')
    precio_max = fields.Float("Maximun Price", digits=(16, 2), default="0.00")
    text_publi = fields.Char("Texto")
    state_publi = fields.Selection([
        ('activo', 'Active'),
        ('inactivo', 'Inactive')
    ], string="Estado de la publicacion", )


    # Campo `rule_id` con número aleatorio persistente
    rule_id = fields.Char("Regla ID", readonly=True)
    data_type = fields.Char("What kind of data is this one")  # Competencia O Gestor

    rule_price_exact =  fields.Float(string='Precio', digits=(16, 2), default="10.00")
    """ incremento_precio = fields.Selection(
        [('5', '5%'), ('10', '10%'), ('15', '15%'), ('20', '20%'), ('25', '25%'), 
         ('30', '30%'), ('35', '35%'), ('40', '40%'), ('45', '45%'), ('50', '50%'), 
         ('55', '55%'), ('60', '60%'), ('65', '65%'), ('70', '70%'), ('75', '75%'), 
         ('80', '80%'), ('85', '85%'), ('90', '90%'), ('95', '95%'), ('100', '100%')],
        string="Incremento de Precio"
    ) """
    incremento_precio_input = fields.Float('Incremento de Precio')
    gain_flat_value = fields.Float('gain_flat_value', digits=(16, 2), default="0.00")
    gain_percentage_value = fields.Float('gain_percentage_value')
    is_rule_active = fields.Boolean(string='Activo', default=True)

    product_name = fields.Char(string="Nombre del Producto", related="product.name", store=True)
    product_actual_price = fields.Float(string="Precio Actual del Producto", related="product.list_price", store=True)
    numero_competencias = fields.Integer(string="Numero de Competencias")

    competence_actual_price = fields.Float(string="Precio Actual de la Competencia") 

    is_competence_active = fields.Boolean(string='Activo', default=True)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self._get_currency())
    texto_resumen = fields.Char('texto resumen')
    texto_precio = fields.Char('texto precio')
    new_price = fields.Float('New price', digits=(16, 2), default="0.0")
    meli_fee = fields.Float('Meli fee', digits=(16, 2), default="0.0")

    products_compared = fields.One2many(
        'mercado.libre.product.compared',
        'parent_id', 
        string="Productos Comparados"
    )
    type_rule = fields.Selection([
        ('manual', 'Manual'),
        ('auto', 'Automatic')
    ], string="Type Rule", )
    is_automatic_type = fields.Boolean('is Automatic Type?', default=True, tracking=True)
    exist_gain = fields.Boolean('Is there any gain?', tracking=True)
    exist_max_price = fields.Boolean('existe maximo precio?', default=True, tracking=True)
    want_profit = fields.Boolean('want profit?', default=False, tracking=True)
    instance_id = fields.Many2one('vex.instance', string='instance', default=lambda self: self.env.user.meli_instance_id)
    price_score = fields.Char(
        string="Price Score",
        compute="_compute_price_category",
        store=True
    )

    @api.model
    def create(self, vals):
        """ Generamos un rule_id aleatorio solo si no se ha asignado antes. """
        _logger.info("VALS CREATE: %s",vals)
        return super(MercadoLibreProduct, self).create(vals)    
    
    @api.model
    def _get_currency(self):
        instance = self.env.user.meli_instance_id
        _logger.info(f"Obteniendo currency desde instance: {instance}")
        if instance and instance.default_currency:
            _logger.info(f"default_currency encontrado: {instance.default_currency}")
            Currency = self.env['res.currency']

            # Búsqueda por name
            currency = Currency.with_context(active_test=False).sudo().search(
                [('name', '=', instance.default_currency)],
                limit=1
            )
            if not currency:
                _logger.warning(f"No se encontró currency con name={instance.default_currency}")
                # Búsqueda alternativa por código ISO (currency_code si aplica)
                if 'currency_code' in Currency._fields:
                    currency = Currency.search([('currency_code', '=', instance.default_currency)], limit=1)
                    if currency:
                        _logger.info(f"Moneda encontrada por currency_code: {currency.name}")
            else:
                _logger.info(f"Moneda encontrada: {currency.name} ({currency.symbol})")
            
            return currency.id if currency else None

        _logger.warning("No se pudo obtener la currency: instance o default_currency no definidos")
        return None
    @api.depends('product')
    def _compute_name(self):
        for record in self:
            record.name = record.product.name if record.product else ''

    @api.onchange('product')
    def _onchange_product(self):
        if self.product:
            self.action_calculate_price_limits()

    @api.onchange('incremento_precio_input')
    def _check_incremento_precio_input(self):
        for record in self:
            if record.precio_opcion=="porcentaje":
                if record.incremento_precio_input*100 < 1 or record.incremento_precio_input*100 > 100:
                    raise ValidationError("The percentage value must be between 1 and 100.")

    @api.onchange('gain_percentage_value')
    def _check_gain_percentage_value(self):
        for record in self:
            if record.ganancia_opcion=="porcentaje":
                if record.gain_percentage_value*100 < 1 or record.gain_percentage_value*100 > 100:
                    raise ValidationError("The percentage value must be between 1 and 100.")
    
    @api.model
    def get_score_letter(self):
        for record in self:
            score_counts = self.read_group(
                [('price_score', 'in', ['A', 'B', 'C'])],
                ['price_score'],
                ['price_score']
            )
            
            count_A = count_B = count_C = 0

            for count in score_counts:
                if count['price_score'] == 'A':
                    count_A = count['__count']
                elif count['price_score'] == 'B':
                    count_B = count['__count']
                elif count['price_score'] == 'C':
                    count_C = count['__count']
            
            total_records = count_A + count_B + count_C
            if total_records == 0:
                return 'C'

            # A=3, B=2, C=1
            score = (count_A * 3 + count_B * 2 + count_C * 1) / total_records
            
            if score >= 2.5:
                return 'A'
            elif score >= 1.5:
                return 'B'
            else:
                return 'C'
            
    @api.depends('products_compared.price', 'new_price')
    def _compute_price_category(self):
        for record in self:
            prices = record.products_compared.mapped('price')
            if not prices:
                record.price_score = None
                continue
            
            avg_price = sum(prices) / len(prices)

            if record.new_price > avg_price:
                record.price_score = 'A'
            elif record.new_price < avg_price:
                record.price_score = 'C'
            else:
                record.price_score = 'B'
    
    @api.model
    def get_all_products_with_avg_compared(self):
        result = []
        all_products = self.search([('state_publi', '!=', None)])  # traer todos los registros

        for record in all_products:
            prices = record.products_compared.mapped('price')
            avg_price = sum(prices) / len(prices) if prices else 0

            result.append({
                'product_name': record.product.name,
                'standard_price': record.product.standard_price,
                'avg_compared_price': round(avg_price, 2),
            })

        return result

    @api.model
    def get_all_profit_margins(self):
        productos = self.search([])
        margenes = []

        for prod in productos:
            precio_venta = prod.product.list_price or 0
            costo = prod.product.standard_price or 0
            comision = prod.meli_fee or 0  # ajusta el nombre si es diferente

            if precio_venta == 0:
                margen = 0
            else:
                utilidad = precio_venta - costo - comision
                margen = (utilidad / precio_venta) * 100

            margenes.append(round(margen, 2))

        return margenes

    @api.model
    def get_average_profit_margin(self):
        margenes = self.get_all_profit_margins()
        if not margenes:
            return 0
        return round(sum(margenes) / len(margenes), 2)

    @api.model
    def get_percentage_below_average(self):
        productos = self.search([])
        total = len(productos)
        if total == 0:
            return 0.0

        count_below_avg = 0

        for prod in productos:
            prices = prod.products_compared.mapped('price')
            if not prices:
                continue 

            avg_price = sum(prices) / len(prices)
            if prod.new_price < avg_price:
                count_below_avg += 1

        porcentaje = (count_below_avg / total) * 100
        return round(porcentaje, 2)

    @api.model
    def get_percentage_in_average(self):
        productos = self.search([])
        total = len(productos)
        if total == 0:
            return 0.0

        count_in_avg = 0

        for prod in productos:
            prices = prod.products_compared.mapped('price')
            if not prices:
                continue 

            avg_price = sum(prices) / len(prices)
            if prod.new_price == avg_price:
                count_in_avg += 1

        porcentaje = (count_in_avg / total) * 100
        return round(porcentaje, 2)
    
    @api.model
    def get_percentage_above_average(self):
        productos = self.search([])
        total = len(productos)
        if total == 0:
            return 0.0

        count_above_avg = 0

        for prod in productos:
            prices = prod.products_compared.mapped('price')
            if not prices:
                continue 

            avg_price = sum(prices) / len(prices)
            if prod.new_price > avg_price:
                count_above_avg += 1

        porcentaje = (count_above_avg / total) * 100
        return round(porcentaje, 2)
    
    @api.model
    def get_profit_margin_evolution(self):
        today = datetime.today()
        result = defaultdict(list)
        months_labels = []
        margins_by_month = {}

        for i in range(5, -1, -1):
            date_start = (today - relativedelta(months=i)).replace(day=1)
            date_end = (date_start + relativedelta(months=1)) - timedelta(days=1)
            label = date_start.strftime('%b')
            months_labels.append(label)

            records = self.search([
                ('create_date', '>=', date_start.strftime('%Y-%m-%d 00:00:00')),
                ('create_date', '<=', date_end.strftime('%Y-%m-%d 23:59:59')),
                ('type_rule', '=','manual')
            ])

            margins = []
            for rec in records:
                sale_price = rec.new_price or rec.product.list_price
                cost = rec.product.standard_price or 0.0
                commission = rec.meli_fee or 0.0

                if sale_price > 0:
                    margin = ((sale_price - (cost + commission)) / sale_price) * 100
                    margins.append(margin)

            average_margin = round(sum(margins) / len(margins), 2) if margins else 0.0
            margins_by_month[label] = average_margin

        return {
            'months': months_labels,
            'profitMargins': [margins_by_month[m] for m in months_labels]
        }
    
    @api.model
    def get_price_evolution_grouped(self):
        """Retorna un diccionario con la evolución de los precios agrupados por mes para todos los productos."""
        records = self.env['mercado.libre.product'].search([])

        monthly_data = defaultdict(lambda: {'our_prices': [], 'competitor_prices': []})

        for rec in records:
            month_str = rec.create_date.strftime('%B') 

            if rec.new_price:
                monthly_data[month_str]['our_prices'].append(rec.new_price)

            for competitor in rec.products_compared:
                if competitor.price:
                    monthly_data[month_str]['competitor_prices'].append(competitor.price)

        sorted_months = sorted(monthly_data.keys(), key=lambda m: datetime.strptime(m, '%B').month)
        result = {
            'months': sorted_months,
            'ourPrices': [],
            'competitorPrices': []
        }

        for month in sorted_months:
            data = monthly_data[month]
            our_avg = round(sum(data['our_prices']) / len(data['our_prices']), 2) if data['our_prices'] else 0
            competitor_avg = round(sum(data['competitor_prices']) / len(data['competitor_prices']), 2) if data['competitor_prices'] else 0

            result['ourPrices'].append(our_avg)
            result['competitorPrices'].append(competitor_avg)

        return result

    @api.model
    def get_daily_sales_evolution(self):
        """Devuelve la evolución de ventas (monto total) por día del mes actual para órdenes tipo MercadoLibre."""
        SaleOrder = self.env['sale.order']

        today = datetime.today()
        first_day = today.replace(day=1)
        month = today.month
        year = today.year

        orders = SaleOrder.search([
            ('store_type', '=', 'mercadolibre'),
            ('date_order', '>=', first_day),
            ('date_order', '<', today.replace(month=month % 12 + 1, day=1) if month < 12 else today.replace(year=year+1, month=1, day=1)),
            ('state', 'in', ['sale', 'done']) 
        ])

        daily_sales = defaultdict(float)

        for order in orders:
            day_str = f"Day{order.date_order.day}"
            daily_sales[day_str] += order.amount_total

        result = {
            'days': [],
            'sales': []
        }

        for day in range(1, 32):
            label = f'Day{day}'
            result['days'].append(label)
            result['sales'].append(round(daily_sales.get(label, 0.0), 2))

        return result

    @api.model
    def get_monthly_profit_growth(self):
        SaleOrder = self.env['sale.order']
        today = datetime.today()
        first_day_this_month = today.replace(day=1)
        first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)

        # Primer día del siguiente mes al anterior (es decir, fin del mes pasado)
        first_day_next_month_last = first_day_this_month
        first_day_next_month_current = (first_day_this_month.replace(day=28) + timedelta(days=4)).replace(day=1)

        # Filtrar órdenes de cada mes
        orders_last_month = SaleOrder.search([
            ('date_order', '>=', first_day_last_month),
            ('date_order', '<', first_day_next_month_last),
            ('store_type', '=', 'mercadolibre')
        ])
        orders_this_month = SaleOrder.search([
            ('date_order', '>=', first_day_this_month),
            ('date_order', '<', first_day_next_month_current),
            ('store_type', '=', 'mercadolibre')
        ])

        # Calcular totales (puedes cambiar amount_total por utilidad si la tienes)
        total_last_month = sum(orders_last_month.mapped('amount_total'))
        total_this_month = sum(orders_this_month.mapped('amount_total'))

        if total_last_month == 0:
            return 100.0 if total_this_month > 0 else 0.0

        growth_percentage = ((total_this_month - total_last_month) / total_last_month) * 100
        return round(growth_percentage, 2)

    @api.model
    def get_total_products(self):
        current_user = self.env.user 
        return self.search_count([
            ('state_publi', '!=', None)
        ])
    
    def action_save_data(self):
        _logger.info("Guardando datos")

        datos_guardar = self.read()
        _logger.info(f"Datos a guardar: {datos_guardar}")

        if self.product:
            self.product_id = self.product.id

        if self.is_automatic_type:
            if self.precio_max < self.precio_min:
                self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': "Error",
                    'message': f"The maximum price cannot be less than the minimum price",
                    'type': 'danger'
                }
                )
                return
        self._compute_text_publi()

        datos_guardar_master = {
            'name': self.name,
            'price': self.price,
            'product_url': self.product_url,
            'image': self.image,
            'product_id': self.product.id,
            'product_image': self.product_image,
            'link': self.link,
            'competence_image': self.competence_image,
            'precio_comparacion': self.precio_comparacion,
            'precio_opcion': self.precio_opcion,
            'barato_caro': self.barato_caro,
            'precio_min': self.precio_min,
            'precio_max': self.precio_max,
            'text_publi': self.text_publi,
            'texto_resumen': self.texto_resumen,
            'rule_price_exact': self.rule_price_exact,
            'incremento_precio_input': self.incremento_precio_input,
            'ganancia_opcion': self.ganancia_opcion,
            'gain_flat_value': self.gain_flat_value,
            'gain_percentage_value': self.gain_percentage_value,
            'state_publi': 'activo',
            'rule_id': self.rule_id,
            'data_type': 'master',
            'is_rule_active': True,
            'new_price': self.new_price,
            'is_automatic_type': self.is_automatic_type,
            'type_rule': 'auto' if self.is_automatic_type else 'manual',
            'price_score': self.price_score
        }
        _logger.info(f"Datos a guardar en master: {datos_guardar_master}")
        
        missing_fields = []
        required_fields = ['product_id', 'precio_comparacion', 'precio_opcion', 'barato_caro', 'precio_min']
        
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        if missing_fields:
            missing_fields_str = ', '.join(missing_fields)
            self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': "Error",
                'message': f"Faltan los siguientes campos requeridos: {missing_fields_str}",
                'type': 'danger'
            }
            )
            raise UserError(f"Faltan los siguientes campos requeridos: {missing_fields_str}")
        registro_existente = self.search([('id','=', self.id)])
        if registro_existente:
            self.sudo().write({
                'name': self.name,
                'price': self.price,
                'product_url': self.product_url,
                'image': self.image,
                'product': self.product.id,
                'product_id': self.product.id,
                'product_image': self.product_image,
                'link': self.link,
                'competence_image': self.competence_image,
                'precio_comparacion': self.precio_comparacion,
                'precio_opcion': self.precio_opcion,
                'barato_caro': self.barato_caro,
                'precio_min': self.precio_min,
                'precio_max': self.precio_max,
                'text_publi': self.text_publi,
                'texto_resumen': self.texto_resumen,
                'rule_price_exact': self.rule_price_exact,
                'incremento_precio_input': self.incremento_precio_input,
                'ganancia_opcion': self.ganancia_opcion,
                'gain_flat_value': self.gain_flat_value,
                'gain_percentage_value': self.gain_percentage_value,
                'state_publi': 'activo',
                'rule_id': self.rule_id,  # Mantenemos el rule_id
                'data_type': 'master',  # Importante
                'new_price': self.new_price,
                'is_automatic_type': self.is_automatic_type,
                'type_rule': 'auto' if self.is_automatic_type else 'manual',
                'price_score': self.price_score
            })
        else:
            self.env['mercado.libre.product'].create({
                'name': self.name,
                'price': self.price,
                'product_url': self.product_url,
                'image': self.image,
                'product': self.product.id,
                'product_id': self.product.id,
                'product_image': self.product_image,
                'link': self.link,
                'competence_image': self.competence_image,
                'precio_comparacion': self.precio_comparacion,
                'precio_opcion': self.precio_opcion,
                'barato_caro': self.barato_caro,
                'precio_min': self.precio_min,
                'precio_max': self.precio_max,
                'text_publi': self.text_publi,
                'texto_resumen': self.texto_resumen,
                'rule_price_exact': self.rule_price_exact,
                'incremento_precio_input': self.incremento_precio_input,
                'ganancia_opcion': self.ganancia_opcion,
                'gain_flat_value': self.gain_flat_value,
                'gain_percentage_value': self.gain_percentage_value,
                'state_publi': 'activo',
                'rule_id': self.rule_id,  # Mantenemos el rule_id
                'data_type': 'master',  # Importante
                'new_price': self.new_price,
                'is_automatic_type': self.is_automatic_type,
                'type_rule': 'auto' if self.is_automatic_type else 'manual',
                'price_score': self.price_score
            })
            prod = self.env['product.template'].search([('id','=', self.product.id)])
            prod.sudo().write({
                'price_score': self.price_score,
                'market_fee': self.meli_fee,
                'list_price': self.new_price,
            })
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': "Regla Lista",
                'message': f"Se acaba de crear una regla para el sistema de precios automaticos",
                'type': 'success'
            }
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mercado.libre.product',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current'
        }

    def get_products_from_api(self):
        # URL de la API de Mercado Libre para obtener productos
        url = 'https://api.mercadolibre.com/sites/MLA/search?q=vehiculos&limit=10' 
        _logger.error(link)
        _logger.error(url)
        headers = {'Authorization': 'Bearer {}'.format(self.env['ir.config_parameter'].sudo().get_param('mercadolibre.access_token'))}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    # Verificamos si el producto ya existe en la base de datos
                    existing_product = self.search([('product_url', '=', item['permalink'])])
                    if not existing_product:
                        # Obtenemos la URL de la imagen
                        image_url = item.get('thumbnail', '')

                        # Si hay una imagen, la descargamos y convertimos a base64
                        if image_url:
                            image_data = requests.get(image_url).content
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                        else:
                            image_base64 = False
                        _logger.error("Imagen Base64: %s", item['thumbnail'])

                        # Creamos un nuevo producto y le asignamos la imagen en base64
                        self.create({
                            'product_name': item['title'],
                            'price': item['price'],
                            'product_url': item['permalink'],
                            'image': image_base64,  # Asignamos la imagen en base64
                        })
        except Exception as ex:
            _logger.error("Error al obtener productos de Mercado Libre: %s", ex)

    @api.depends("product")
    def _compute_product_image(self):
        for record in self:
            record.product_image = record.product.image_1920 if record.product else False

    @api.onchange('link')
    def pruebas(self):
        _logger.info("Iniciando pruebas")
        #url_ ="https://articulo.mercadolibre.com.mx/MLM-2876206672-botas-mujer-trabajo-casquillo-negras-cafes-ram-401-d-_JM#reco_item_pos=2&reco_backend=item_decorator&reco_backend_type=function&reco_client=home_items-decorator-legacy&reco_id=88427083-22fa-49e4-bd69-3707e59eae68&reco_model=&c_id=/home/bookmarks-recommendations-seed/element&c_uid=54c7b295-40da-4aa6-9cd0-9169d6e051d8&da_id=bookmark&da_position=2&id_origin=/home/dynamic_access&da_sort_algorithm=ranker"
        url = str(self.link)
        _logger.info(f"Este es el URL a usar {url}")
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        meli_instance.get_access_token()
        access = meli_instance.access_token
        #access = instance = self.env['vex.instance'].search([('store_type', '=', 'mercadolibre')], limit=1) # Idea original
        #access = self.env['vex.instance'].search([('id', '=', 5)], limit=1).access_token

        product_info = self.get_product_info(product_url=url,access_token=access)
        _logger.info(product_info)

        try:
            if product_info:
                # Asignar nombre y precio al producto
                #self.name = product_info.get('title', 'Name not available')
                #self.price = product_info.get('price', 0.0)  # Asigna 0.0 si no tiene precio

                # Extraer información
                nombre = product_info.get("name", "Name not available")
                precio = product_info.get("buy_box_winner", {}).get("price", "Price not available")
                moneda = product_info.get("buy_box_winner", {}).get("currency_id", "MXN")
                image_url = product_info.get("pictures", [{"url": None}])[0]["url"]

                self.product_name = nombre
                self.price = precio

                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    # Convertir la imagen a base64
                    image_base64 = base64.b64encode(image_response.content).decode("utf-8")
                    
                    # Guardar la imagen en el campo Binary
                    self.competence_image = image_base64

                    if self.competence_image:
                        _logger.info("Imagen guardada de competencia en su field correctamente")

                _logger.info(f"Nombre del producto: {self.product_name}")
                _logger.info(f"Precio del producto: {self.price}")
            else:
                _logger.info("No se pudo obtener la información del producto.")
        except Exception as e:
            _logger.info(f"Error al asignar la información del producto: {str(e)}")
        
    def get_product_info(self, product_url: str, access_token):
        """
        Obtiene la información de un producto en Mercado Libre dado un link.

        :param product_url: URL del producto en Mercado Libre.
        :return: JSON con la información del producto o None en caso de error.
        """
        _logger.info("Iniciando obtención de información del producto.")

        # Extraer el ID del producto
        meli_id = product_url.split("/")[-1].split("#")[0]

        if "/p/" in product_url:
            producto_id = product_url.split("/p/")[-1].split("?")[0].split("#")[0]
            api_url = f"https://api.mercadolibre.com/products/{producto_id}"
        else:
            partes_url = product_url.split("/")
            item_id = None
            for parte in partes_url:
                if parte.startswith("MLM"):
                    item_id = parte
                    break
            
            if not item_id:
                return {"Error": "No se pudo extraer el ID del producto"}

            api_url = f"https://api.mercadolibre.com/items/{item_id}"

        _logger.info("Api url a usar")
        
        if not meli_id:
            _logger.error("No se pudo extraer el ID del producto de la URL.")
            return None
        
        url = api_url
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            _logger.info(f"Solicitando información del producto con ID: {meli_id}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            _logger.info("Información del producto obtenida correctamente.")
            return response.json()
        
        except requests.RequestException as e:
            _logger.error(f"Error al obtener la información del producto: {str(e)}")
            return None
        
    def extract_meli_id(self, url: str) -> str:
        """
        Extrae el ID de un producto de una URL de Mercado Libre.

        :param url: URL del producto en Mercado Libre.
        :return: ID del producto (MELI ID) o None si no se puede extraer.
        """
        match = re.search(r'/ML[ABM]-\d+', url)
        if match:
            valor = match.group().strip("/")
            valor = valor.replace("-", "")
            return  valor # Devuelve el ID sin los slashes
        return None
    
    def action_save_and_add_competence(self):
        competence = self.env['mercado.libre.product.compared'].search([
            ('parent_id', '=', self.id),
            ('link', '=', self.link)
            ])
        if competence:
            raise UserError("This link has already been used. Enter a new one.")
        else:
            self.env['mercado.libre.product.compared'].create({
                'name': self.product_name,
                'price': self.price,
                'link': self.link,
                'image': self.competence_image,
                'parent_id': self.id,
                'currency_id': self.currency_id.id
            })        

        competence_count = self.env['mercado.libre.product.compared'].search_count([
            ('parent_id', '=', self.id)
        ])

        #sI NO existe el name o price = 0 suelta user error
        if self.product_name == False or self.price == 0:
            raise UserError("This product is not compatible with the competition rule")

               
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
            'title': "Updated Rule",
            'message': f"This rule is being applied to {competence_count} competencies. Product: {self.product_name}, Price: {self.price}",
            'type': 'success'
            }
        )


        # Limpiamos solo los campos especificados del producto de la competencia
        self.write({
            'link': False,
            'competence_image': False,
            'name' : False,
            'price' : False
        })

        self.action_calculate_new_price()

        # 🔹 Hacemos un commit para que la notificación se ejecute antes de refrescar la vista
        #self.env.cr.commit()
    
    def action_show_notification(self):
        """ Envía una notificación en tiempo real al usuario actual sin return """
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,  # Enviar solo al usuario actual
            'simple_notification',  # Canal de notificación
            {
                'title': "Regla Actualizada",
                'message': "Se ha actualizado correctamente la regla y la vista.",
                'type': 'success'  # Tipos: success, warning, danger, info
            }
        )  

    def show_specific_succes_notification(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': message,
                'type': 'success',  # Tipos: success, warning, danger, info
                'sticky': False,    # True para mantener el mensaje visible hasta que el usuario lo cierre
            },
        }

    @api.onchange('precio_min')
    def _onchange_precio_min(self):
        self.sudo().write({
            'precio_min': self.precio_min
        })

    @api.onchange('precio_max')
    def _onchange_precio_max(self):
        self.sudo().write({
            'precio_max': self.precio_max
        })

    @api.onchange('products_compared')
    def _onchange_products_compared(self):
        if not self._origin:
            return
        else:
            self.action_calculate_price_limits()

    def action_calculate_price_limits(self):
        _logger.info("action_calculate_price_limits")
        """ if not self._origin:
            return
        if not self.product:
            raise UserError("First select the product to calculate the limit price") """

        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        meli_instance.get_access_token()
        access = meli_instance.access_token
        _logger.info("product%s",self.product)

        url_prices = f"https://api.mercadolibre.com/sites/{meli_instance.meli_country}/listing_prices?price={self.product.mercado_libre_price}&listing_type_id={self.product.listing_type_id}&category_id={self.product.meli_category_code}"
        url_sug = f"https://api.mercadolibre.com/suggestions/items/{self.product.ml_publication_code}/details"
        headers = {
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
        }
        
        response_prices = requests.get(url_prices, headers=headers)
        if response_prices.status_code == 200:
            response_prices_json = response_prices.json()
            sale_fee_amount = response_prices_json['sale_fee_amount']
            self.meli_fee = sale_fee_amount
            cost_price = self.product.standard_price or 0.0
            self.precio_min = sale_fee_amount + cost_price
            """ if self.ganancia_opcion=="porcentaje" and self.gain_percentage_value!=0.0:
                self.precio_min = sale_fee_amount + cost_price + (self.gain_percentage_value*cost_price)
            elif self.ganancia_opcion=="valor_fijo" and self.gain_flat_value!=0.0:
                self.precio_min = sale_fee_amount + cost_price + self.gain_flat_value
            else:
                raise UserError("Define a gain value") """
        else:
            print(f"Error {response_prices.status_code}: {response_prices.text}")
            _logger.error(f"Error {response_prices.status_code}: {response_prices.text}")
        
        response_sug = requests.get(url_sug, headers=headers)
        if response_sug.status_code == 200:
            response_sug_json = response_sug.json()
            suggested_price = response_sug_json['suggested_price']['amount']
            self.precio_max = suggested_price
            self.exist_max_price = True
        elif response_sug.status_code == 404:
            self.precio_max = 0.0
            self.exist_max_price = False
        else:
            print(f"Error {response_sug.status_code}: {response_sug.text}")
            _logger.error(f"Error {response_sug.status_code}: {response_sug.text}")
        _logger.info(f"PRECIOS {self.precio_min}: {self.precio_max}")
        self.set_price_text()

    @api.onchange('products_compared','precio_comparacion', 'barato_caro','precio_opcion','rule_price_exact','incremento_precio_input')
    def action_calculate_new_price(self):
        _logger.info("action_calculate_new_price")
        for record in self:
            price = 0.0
            if not all([record.barato_caro, record.precio_comparacion, record.precio_opcion]):
                raise ValidationError("You must select an option")
            if not self.products_compared:
                price = 0.0
                continue
            
            if record.precio_comparacion == 'cheapest':
                price = min(self.products_compared.mapped('price'))
            elif record.precio_comparacion == 'most_expensive':
                price = max(self.products_compared.mapped('price'))
            elif record.precio_comparacion == 'average':
                price = sum(self.products_compared.mapped('price')) / len(self.products_compared)

            if record.barato_caro == 'barato':
                if record.precio_opcion == 'porcentaje':
                    price -= price * record.incremento_precio_input 
                elif record.precio_opcion == 'valor_fijo':
                    price -= record.rule_price_exact
            elif record.barato_caro == 'caro':
                if record.precio_opcion == 'porcentaje':
                    price += price * record.incremento_precio_input
                elif record.precio_opcion == 'valor_fijo':
                    price += record.rule_price_exact
        self.new_price = price
        _logger.info("new price : %s", record.new_price)
        self.set_price_text()
        _logger.info("texto_precio: %s", self.texto_precio)
    
    @api.onchange('product','precio_comparacion', 'barato_caro')
    def _compute_summary_text(self):
        for record in self:
            if not record.barato_caro or not record.precio_comparacion:
                raise ValidationError("You must select an option")
                record.texto_resumen = "You must select an option"
                continue
            text = 'cheaper' if record.barato_caro == 'barato' else 'more expensive'
            text += ' than '
            comparacion_texts = {
                'cheapest': 'the cheapest publication',
                'most_expensive': 'the most expensive publication',
                'average': 'the average price'
            }
            record.texto_resumen = text + comparacion_texts.get(record.precio_comparacion, '')
    
    @api.onchange('product', 'products_compared')
    def set_price_text(self):
        current_price = self.product.mercado_libre_price
        if self.precio_min == 0.0 and self.new_price == 0.0:
            return ''
        diff_price = self.new_price - self.precio_min
        cur_sym = self.currency_id.symbol
        if diff_price > 0:
            self.exist_gain = True
            self.texto_precio = f"Your current price is {cur_sym} {round(current_price, 2)} and will become {cur_sym} {round(self.new_price, 2)}, The new price is higher than the minimum price, you will have a gain of {cur_sym} {round(diff_price, 2)}."
        else:
            self.exist_gain = False
            self.texto_precio = f"Your current price is {cur_sym} {round(current_price, 2)} and will become {cur_sym} {round(self.new_price, 2)}, The new price is lower than the minimum price, there is a loss of {cur_sym} {round(diff_price*-1, 2)}."
    
    def _compute_text_publi(self):
        for record in self:
            if record.is_automatic_type:
                record.text_publi = f"minimum {record.currency_id.symbol} {record.precio_min} and maximum {record.currency_id.symbol} {record.precio_max}"
            else:
                if record.precio_opcion == 'porcentaje':
                    valor_numero = f"{record.incremento_precio_input*100}%"
                elif record.precio_opcion == 'valor_fijo':
                    valor_numero = f"{record.currency_id.symbol} {record.rule_price_exact}"

                barato_caro_value = dict(self._fields['barato_caro'].selection).get(record.barato_caro, "")
                precio_comparacion_value = dict(self._fields['precio_comparacion'].selection).get(record.precio_comparacion, "")

                record.text_publi = f"{valor_numero} {barato_caro_value} than {precio_comparacion_value}"


    def update_mercadoLibre_price(self):
        _logger.info("STARTS CRON update_mercadoLibre_price")
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            instance.get_access_token()
            access = instance.access_token
            for item_pricing in self.env['mercado.libre.product'].search([('instance_id','=',instance.id),('state_publi','=','activo')]):
                _logger.info("Starts Item Pricing: %s", item_pricing.name)
                url_item = f"https://api.mercadolibre.com/items/{item_pricing.product.ml_publication_code}"
                url_auto = f"https://api.mercadolibre.com/pricing-automation/items/{item_pricing.product.ml_publication_code}/rules"
                headers = {
                    "Authorization": f"Bearer {access}",
                    "Content-Type": "application/json",
                }
                cur_sym = item_pricing.currency_id.symbol
                if item_pricing.is_automatic_type:
                    _logger.info("Price Adjustment Type: Automatic.")
                    cost_price = item_pricing.product.standard_price or 0.0
                    if item_pricing.want_profit:
                        if item_pricing.ganancia_opcion=="porcentaje":
                            _logger.info(f"For this item, {cur_sym} {item_pricing.gain_percentage_value*cost_price} gain is being considered at the minimum price.")
                            item_pricing.precio_min += (item_pricing.gain_percentage_value*cost_price)
                        elif item_pricing.ganancia_opcion=="valor_fijo":
                            _logger.info(f"For this item, {cur_sym} {item_pricing.gain_flat_value} gain is being considered at the minimum price.")
                            item_pricing.precio_min += item_pricing.gain_flat_value
                    payload = {
                        "rule_id": "INT",
                        "min_price": item_pricing.precio_min,
                        "max_price": item_pricing.precio_max
                    }
                    _logger.info(f"Set as automatic price with: {cur_sym} {item_pricing.precio_min} minimum price and {cur_sym} {item_pricing.precio_max} maximum price.")
                    response_auto = requests.post(url_auto, headers=headers, data=json.dumps(payload))

                    if response_auto.status_code == 200:
                        _logger.info("Price automation correctly implemented in MercadoLibre.")
                    else:
                        error_msg = response_auto.json().get("message", "Error desconocido")
                        raise UserError(f"Error applying price automation: {error_msg}")
                else:
                    _logger.info("Price Adjustment Type: Manual")
                    payload_item = json.dumps({"price": item_pricing.new_price})
                    _logger.info("The new price to be updated is: %s", item_pricing.new_price)
                    response_item = requests.put(url_item, headers=headers, data=payload_item)
                    if response_item.status_code == 200:
                        _logger.info("Correctly updated manual price on MercadoLibre.")
                        old_price = item_pricing.product.list_price
                        new_price = item_pricing.new_price
                        if old_price != new_price:
                            self.env['vex.soluciones.price.evolution.data'].create({
                                'product_id': item_pricing.product.id,
                                'old_price': old_price,
                                'new_price': new_price,
                                'change_date': fields.Datetime.now(),
                            })
                    else:
                        error_msg = response_item.json().get("message", "Error desconocido")
                        raise UserError(f"Error updating price on MercadoLibre.: {error_msg}")
                _logger.info("Ends Item Pricing: %s", item_pricing.name)
        _logger.info("ENDS CRON update_mercadoLibre_price")

class MercadoLibreProductCompared(models.Model):
    _name = 'mercado.libre.product.compared'

    name = fields.Char("Name")
    price = fields.Float("Price")
    link = fields.Text("Mercado Libre Link")
    image = fields.Binary("IMG", store=True)
    currency_id = fields.Many2one("res.currency", string="Currency")
    parent_id = fields.Many2one('mercado.libre.product', string="Registro Padre", ondelete="cascade")
        
    @api.model
    def create(self, vals):
        record = super(MercadoLibreProductCompared, self).create(vals)
        #record.parent_id.action_calculate_new_price()
        return record
    
    def unlink(self):
        parents = self.mapped('parent_id')
        result = super(MercadoLibreProductCompared, self).unlink()
        for parent in parents:
            #parent.action_calculate_price_limits()
            parent.action_calculate_new_price()
        return result
    
    @api.model
    def get_total_competitors(self):
        current_user = self.env.user 
        return self.search_count([
            ('parent_id.instance_id', '=', current_user.meli_instance_id.id),
            ('parent_id.state_publi', '=', 'activo')
        ])