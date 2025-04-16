from odoo import fields, models, api
from datetime import datetime
import requests
import json
import base64
import time
import logging
_logger = logging.getLogger(__name__)
class VexSynchro(models.Model):
    _name="vex.synchro"


    def sync_import(self):
        count = 0  # Contador de iteraciones

        ## Updateamos todos los tokens de todas las instancias
        
        for instance in self.env['vex.instance'].search([]):
            if instance.store_type == 'mercadolibre':
                _logger.info("Checking Tokens for Mercado Libre instance")
                self.update_token(instance)


        #time.sleep(100000)
        while count < 19:
            #_logger.info("Iniciando ciclo de sincronización...")
            try:
                import_line_id = self.env['vex.import_line'].search(
                    [
                        ('status', 'in', ['pending']),  
                        ('store_type', '=', 'mercadolibre')  
                    ],
                    order='id DESC',  
                    limit=1          
                )
                if import_line_id:        
                    if import_line_id.action == 'product':
                        self.sync_product(import_line_id)
                        count += 1  # Incrementa el contador si se sincroniza un producto

                    elif import_line_id.action == 'order':
                        dato = self.sync_order(import_line_id)
                        if dato == "pass":
                            _logger.info("PASS DETECTED")
                            # Si se detecta 'pass', se mantiene el contador igual
                            continue  # Salta al siguiente ciclo sin incrementar
                        else:
                            count += 1  # Incrementa el contador si no es 'pass'
                else:
                    # Si no se encuentra ninguna línea de importación, se puede incrementar el contador para evitar un ciclo infinito
                    count += 1
            except Exception as e:
                _logger.error(f"Error en el proceso de sincronización: {str(e)}")
                # Incrementa el contador para evitar que el ciclo quede atrapado si hay un error
                count += 1



    def _create_or_update_stock(self, product_id, stock_qty, stock_location, debug=False):
        """
        Crea o actualiza el stock de un producto en una ubicación específica.
        Si la ubicación no existe, la crea con el nombre proporcionado.

        :param product_id: ID del producto.
        :param stock_qty: Cantidad de stock a establecer.
        :param stock_location: Nombre de la ubicación donde se debe actualizar/crear el stock.
        :param debug: Si es True, activa los logs para esta función.
        """
        log = _logger.info if debug else lambda *args, **kwargs: None  # Log solo si debug es True

        log("Iniciando proceso para actualizar/crear stock para el producto ID: %s en la ubicación: %s", product_id, stock_location)

        StockQuant = self.env['stock.quant']
        StockLocation = self.env['stock.location']
        Product = self.env['product.product']

        # Verificar si el producto existe
        product = Product.browse(product_id)
        if not product.exists():
            _logger.error("No se encontró un producto con el ID: %s", product_id)  # Siempre log de error
            raise ValueError(f"No se encontró un producto con el ID: {product_id}")

        log("Producto encontrado: %s (ID: %s)", product.name, product.id)

        # Buscar o crear la ubicación
        location = StockLocation.search([('name', '=', stock_location)], limit=1)
        if not location:
            log("La ubicación '%s' no existe. Creándola ahora.", stock_location)
            location = StockLocation.create({
                'name': stock_location,
                'usage': 'internal',
            })
            log("Ubicación creada con éxito: %s (ID: %s)", location.name, location.id)

        location_id = location.id
        log("Ubicación seleccionada: %s (ID: %s)", location.complete_name, location_id)

        # Buscar el stock.quant para el producto y la ubicación
        quant = StockQuant.search([('product_id', '=', product.id), ('location_id', '=', location_id)], limit=1)

        if quant:
            log("Se encontró un stock.quant existente. Actualizando cantidad de %s a %s", quant.quantity, stock_qty)
            quant.quantity = stock_qty
        else:
            log("No se encontró un stock.quant para el producto %s en la ubicación %s. Creando uno nuevo.", product.name, location.complete_name)
            StockQuant.create({
                'product_id': product.id,
                'location_id': location_id,
                'quantity': stock_qty,
            })
            log("Nuevo stock.quant creado para el producto %s con cantidad %s en la ubicación %s.", product.name, stock_qty, location.complete_name)

        log("Proceso de actualización/creación de stock completado con éxito.")


    
    def update_token(self, instance):
        access_token = instance.access_token
        user_info_url = 'https://api.mercadolibre.com/users/me'
        res = requests.get(user_info_url, params={'access_token': access_token})

        if res.status_code == 200:
            _logger.info("Token up to date")
            pass
        else:
            url = 'https://api.mercadolibre.com/oauth/token?grant_type=authorization_code&client_id={}&client_secret={}&code={}&redirect_uri={}'.format(instance.app_id, instance.secret_key, instance.server_code,instance.redirect_uri)

            _logger.info("Getting acces token")
            if instance.refresh_token:
                _logger.info("Refresh token logic")
                url = 'https://api.mercadolibre.com/oauth/token'
                data = {
                    'grant_type': 'refresh_token',
                    'client_id': instance.app_id,
                    'client_secret': instance.secret_key,
                    'refresh_token': instance.refresh_token  # tUse the refresh_token stored in the instance
                }

                # Make the POST request with the required parameters
                try:
                    _logger.info("URL: %s", url)
                    _logger.info(f"trans: {data}")
                    response = requests.post(url, data=data)
                    _logger.info(f"Nuevos tokens {response.text}")
                    if response.status_code == 200:
                        json_obj = json.loads(response.text)
                        if 'access_token' in json_obj:
                            _logger.info(f" { json_obj['access_token']}  <--->   {json_obj['refresh_token']}")
                            instance.sudo().write({'access_token': json_obj['access_token']})
                            instance.sudo().write({'refresh_token': json_obj['refresh_token']})

                            _logger.info("Refreshed token")
                    else:                        
                        _logger.error(f"Error refreshing Access Token. Response code:{response.status_code} - {response.text}")
                except Exception as ex:
                    _logger.error(f"Error refreshing Access Token.{ex}")


                return
            try:
                response = requests.post(url)
                _logger.info("URL: %s", url) 
                if response.status_code == 200:
                    json_obj = json.loads(response.text)
                    if 'access_token' in json_obj:
                        self.write({
                            'access_token': json_obj['access_token'],
                            'refresh_token': json_obj['refresh_token'],
                        })
                else:                    
                    _logger.error(response.text)
            except Exception as ex:
                _logger.error(f"Error obtaining Access Token. {ex}")
            

    def sync_product(self, import_line_id):
        _logger.info(import_line_id.description)

        log_id = self.create_log(import_line_id.description)

        try:
            start_time = datetime.today()
            headers = self._get_headers(import_line_id.instance_id.access_token)
            url_item = f"https://api.mercadolibre.com/items?ids={import_line_id.description}"

            response_item = requests.get(url_item, headers=headers)
            if response_item.status_code != 200:
                raise Exception(f"Error al obtener el item: {response_item.text}")

            items = json.loads(response_item.text)

            for item in items:
                self.process_item(item, import_line_id, headers, start_time)

            import_line_id.write({'status': 'done'})
            log_id.write({'state': 'done'})
        except Exception as ex:
            _logger.error(f"Error en sync_product: {ex}")
            import_line_id.write({'status': 'error'})
            log_id.write({'state': 'error'})
        finally:
            end_time = datetime.today()
            import_line_id.write({'start_date': start_time, 'end_date': end_time})
            log_id.write({'start_date': start_time, 'end_date': end_time})


    def create_log(self, description):
        return self.env['vex.meli.logs'].create({
            'description': description,
            'action_type': 'Product',
            'vex_restapi_list_id': self.env.ref('odoo-mercadolibre.meli_action_products').id
        })


    def _get_headers(self, access_token):
        return {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {access_token}'
        }


    def process_item(self, item, import_line_id, headers, start_time):
        log_product_id = self.create_log(import_line_id.description)
        state = True
        msg = ""

        if item['code'] != 200:
            msg = f"Request error: {item['code']}"
            _logger.warning(msg)
            state = False
            log_product_id.write({'state': 'error', 'description': msg})
            return

        item_data = item['body']
        existing_product_id = self._find_existing_product(item_data['id'], import_line_id.instance_id.id)
        attributes, ml_reference = self._process_attributes(item_data['attributes'])
        attribute_value_tuples = self._create_or_update_attributes(attributes, import_line_id.instance_id.id)

        image_1920 = self._fetch_image(item_data['pictures']) if import_line_id.images_import else None
        category_id = self._ensure_category(item_data['category_id'], headers, import_line_id.instance_id.id)

        sku_id = self._get_or_create_sku(ml_reference, import_line_id.instance_id.id)
        stock_location_obj = self._get_stock_location(item_data['shipping']['logistic_type'])

        marketplace_fee = self._get_marketplace_fee(headers, item_data['price'], item_data['listing_type_id'], item_data['category_id'], import_line_id.instance_id.id)
        _logger.info('marketplace_fee%s',marketplace_fee)
        
        product_values = self._prepare_product_values(
            item_data, category_id, image_1920, attribute_value_tuples,
            sku_id, stock_location_obj, ml_reference, marketplace_fee, import_line_id
        )

        if existing_product_id:
            msg = "Actualizando producto"
            _logger.info(msg)
            existing_product_id.write({'attribute_line_ids': [(5, 0, 0)]})
            existing_product_id.write(product_values)
        else:
            msg = "Creando producto"
            existing_product_id = self.env['product.template'].create(product_values)

        self._create_or_update_group_product(existing_product_id, item_data, category_id,
                                            sku_id, ml_reference, image_1920, import_line_id.instance_id.id)

        if import_line_id.stock_import:
            self._update_stock(existing_product_id, item_data)

        log_product_id.write({
            'state': 'done' if state else 'error',
            'start_date': start_time,
            'end_date': datetime.today(),
            'description': msg
        })


    def _find_existing_product(self, meli_code, instance_id):
        return self.env['product.template'].search([
            ('meli_code', '=', meli_code),
            ('instance_id', '=', instance_id)
            #,('active', '=', True)
        ], limit=1)


    def _process_attributes(self, attributes_list):
        attributes = []
        ml_reference = None

        for product in attributes_list:
            if product['id'] == 'SELLER_SKU':
                ml_reference = product['value_name']
            else:
                attributes.append({
                    'name': product['name'],
                    'meli_code': product['id'],
                    'value_name': product['value_name']
                })

        return attributes, ml_reference


    def _create_or_update_attributes(self, attributes, instance_id):
        attribute_value = []

        for attr in attributes:
            attribute = self.env['product.attribute'].search([
                ('meli_code', '=', attr['meli_code']),
                ('instance_id', '=', instance_id)
            ], limit=1)

            if not attribute:
                attribute = self.env['product.attribute'].create({
                    'name': attr['name'],
                    'meli_code': attr['meli_code'],
                    'instance_id': instance_id
                })

            if attr['value_name']:
                value = self.env['product.attribute.value'].search([
                    ('name', '=', attr['value_name']),
                    ('attribute_id', '=', attribute.id),
                    ('instance_id', '=', instance_id)
                ], limit=1)

                if not value:
                    value = self.env['product.attribute.value'].create({
                        'name': attr['value_name'],
                        'attribute_id': attribute.id,
                        'instance_id': instance_id
                    })

                attribute_value.append((attribute.id, value.id))

        return [(0, 0, {'attribute_id': attr_id, 'value_ids': [(6, 0, [val_id])]}) for attr_id, val_id in attribute_value] if attribute_value else False


    def _fetch_image(self, pictures):
        if not pictures:
            return None

        try:
            image_url = pictures[0]['url']
            image_content = requests.get(image_url).content
            return base64.b64encode(image_content).decode('utf-8') if image_content else None
        except Exception as e:
            _logger.warning(f"Error al obtener imagen: {e}")
            return None


    def _ensure_category(self, category_id, headers, instance_id):
        category = self.env['product.category'].search([
            ('meli_code', '=', category_id),
            ('instance_id', '=', instance_id)
        ], limit=1)

        if not category:
            _logger.info(f"Categoría {category_id} no existe. Creándola...")
            wizard = self.env['vex.import.wizard']
            wizard.synchronize_specific_category(category_id, headers)
            category = self.env['product.category'].search([
                ('meli_code', '=', category_id),
                ('instance_id', '=', instance_id)
            ], limit=1)

        return category or self.env.ref('odoo-mercadolibre.category_not_found')


    def _get_or_create_sku(self, ml_reference, instance_id):
        if not ml_reference:
            return False

        sku = self.env['vex.sku'].search([
            ('name', '=', ml_reference),
            ('instance_id', '=', instance_id)
        ], limit=1)

        return sku or self.env['vex.sku'].create({'name': ml_reference, 'instance_id': instance_id})


    def _get_stock_location(self, logistic_type):
        return "FULL Mercado Libre Default" if logistic_type == "fulfillment" else "Default Mercado Libre"

    def _get_marketplace_fee(self, headers, price, listing_type_id, category_id, instance_id):
        instance = self.env['vex.instance'].search([('id', '=', instance_id)])
        code_country = instance.meli_country
        url = f"https://api.mercadolibre.com/sites/{code_country}/listing_prices?price={price}&listing_type_id={listing_type_id}&category_id={category_id}"
        _logger.info(url)
        response = requests.get(url, headers=headers)
        market_fee = 0.0
        if response.status_code == 200:
            res_json = json.loads(response.text)
            market_fee = res_json['sale_fee_amount']
        else:
            _logger.info(response.text)
        return market_fee
    
    def _prepare_product_values(self, item_data, category_id, image_1920, attribute_value_tuples, sku_id, stock_location_obj, ml_reference, marketplace_fee, import_line_id):
        return {
            'categ_id': category_id.id,
            'name': item_data['title'],
            'list_price': item_data['price'],
            'mercado_libre_price': item_data['price'],
            'meli_code': item_data['id'],
            'default_code': item_data['id'],
            'server_meli': True,
            'detailed_type': 'product',
            'image_1920': image_1920,
            'ml_reference': ml_reference,
            'ml_publication_code': item_data['id'],
            'meli_category_code': item_data['category_id'],
            'meli_status': item_data['status'],
            'attribute_line_ids': attribute_value_tuples,
            'sku_id': sku_id.id if sku_id else False,
            'listing_type_id': item_data['listing_type_id'],
            'condition': item_data['condition'],
            'permalink': item_data['permalink'],
            'thumbnail': item_data['thumbnail'],
            'buying_mode': item_data['buying_mode'],
            'inventory_id': item_data.get('inventory_id'),
            'action_export': 'edit',
            'instance_id': import_line_id.instance_id.id,
            'stock_type': stock_location_obj,
            'upc': next((attr['value_name'] for attr in item_data['attributes'] if attr['id'] == 'GTIN'), None),
            'store_type': 'mercadolibre',
            'market_fee': marketplace_fee
        }


    def _create_or_update_group_product(self, existing_product_id, item_data, category_id, sku_id, ml_reference, image_1920, instance_id):
        if not (sku_id and ml_reference):
            return

        group_product = self.env['vex.group_product'].search([
            ('product_id', '=', existing_product_id.id),
            ('instance_id', '=', instance_id)
        ], limit=1)

        group_values = {
            'name': existing_product_id.name,
            'url': item_data['permalink'],
            'num_publication': existing_product_id.meli_code,
            'product_id': existing_product_id.id,
            'image': image_1920,
            'price': existing_product_id.list_price,
            'categ_id': category_id.id,
            'quantity': item_data['available_quantity'],
            'sku_id': sku_id.id,
            'instance_id': instance_id
        }

        if group_product:
            group_product.write(group_values)
        else:
            self.env['vex.group_product'].create(group_values)


    def _update_stock(self, existing_product_id, item_data):
        _logger.info("Actualizando stock")
        stock_qty = item_data['available_quantity']
        logistic_type = item_data['shipping']['logistic_type']
        stock_location = self._get_stock_location(logistic_type)

        product_variant = self.env['product.product'].search([
            ('product_tmpl_id', '=', existing_product_id.id),
            ('active', '=', True)
        ], limit=1)

        if product_variant:
            self._create_or_update_stock(product_variant.id, stock_qty, stock_location, debug=True)




    def _create_and_post_invoice(self, order, json_order,import_line_id):

        invoice_action = import_line_id.instance_id.invoice_action

        if  invoice_action  == 'no_facturar':                
                _logger.info("No se generará factura para el pedido %s", order.id)
                _logger.info(f"Instancia {import_line_id.instance_id} Valor {import_line_id.instance_id.invoice_action} Nombre {import_line_id.instance_id.name}")
                return                                
            
         # Crear la factura desde el pedido de venta
        invoice = order._create_invoices()

        _logger.info(f"Factura creada con ID: {invoice.id} para la orden de venta {order.id}.")
        invoice.action_post()  # Publicar la factura
        _logger.info(f"Factura {invoice.id} publicada.")

        # Registrar comisiones de Mercado Libre y envío
        commission_journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        commission_account = self.env['account.account'].search([('code', '=', 6100)], limit=1)
        shipping_account = self.env['account.account'].search([('code', '=', 6200)], limit=1)

        if not commission_account or not shipping_account:
            _logger.error("No se encontraron las cuentas contables de comisión o envío. Configúralas primero.")
            raise ValueError("Cuentas contables de comisión o envío no configuradas.")


        _logger.info("Iniciando la creación de asientos contables para las comisiones...")
        commission_move = self.env['account.move'].create({
            'journal_id': commission_journal.id,
            'line_ids': [
                # Registro de comisión por envío ($120)
                (0, 0, {
                    'account_id': shipping_account.id,
                    'debit': order.shipping_cost,
                    'credit': 0.0,
                }),
                # Registro de comisión de Mercado Libre ($70)
                (0, 0, {
                    'account_id': commission_account.id,
                    'debit': order.marketplace_fee,
                    'credit': 0.0,
                }),
                # Contrapartida (afecta la cuenta por cobrar)
                (0, 0, {
                    'account_id': self.env['account.account'].search([('code', '=', 1100)], limit=1).id,
                    'debit': 0.0,
                    'credit': order.marketplace_fee+order.shipping_cost,  # Total de comisiones
                }),
            ]
        })
        _logger.info(f"Asientos contables creados con ID: {commission_move.id}")
        _logger.debug(f"Detalles de los asientos contables: {commission_move.line_ids}")
        _logger.info(f"Respectivamente  {order.shipping_cost}     {order.marketplace_fee}")

        # Publicar los asientos contables
        try:
            commission_move.action_post()
            _logger.info(f"Asientos contables para las comisiones publicados exitosamente: {commission_move.id}")
        except Exception as e:
            _logger.error(f"Error al publicar los asientos contables de comisiones: {e}")
            raise


        _logger.info("Registrando el pago")
        self.registrar_pago(invoice)

        
    def registrar_pago(self, invoice):
        """
        Registra un pago para una factura específica.

        :param invoice: Registro de la factura (account.move) a pagar.
        """
        try:
            # Registrar el pago de la factura
            payment = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=invoice.ids
            ).create({
                'amount': invoice.amount_residual,  # Monto pendiente de la factura
                'journal_id': self.env['account.journal'].search([('type', '=', 'cash')], limit=1).id,  # Diario de efectivo
                'payment_date': fields.Date.context_today(self),  # Fecha actual
            })
            payment._create_payments()  # Procesar y registrar el pago
            _logger.info(f"Pago registrado y conciliado para la factura {invoice.id}.")
            return payment
        except Exception as e:
            _logger.error(f"Error al registrar el pago para la factura {invoice.id}: {str(e)}", exc_info=True)
            raise


    def confirm_delivery(self, sale_order_id):
        picking_origin = f"S{sale_order_id}"
        _logger.info(f"Iniciando confirmación de entrega para la orden de venta: {picking_origin}")

        # Buscar los pickings asociados
        pickings = self.env['stock.picking'].search([('origin', '=', picking_origin)])
        if not pickings:
            _logger.warning(f"No se encontraron albaranes asociados a la orden de venta: {picking_origin}")
            return False

        for picking in pickings:
            _logger.info(f"Procesando picking: {picking.name} con estado inicial: {picking.state}")

            if picking.state not in ['done', 'cancel']:
                if picking.state in ['draft', 'waiting']:
                    _logger.info(f"Intentando confirmar el picking: {picking.name}")
                    picking.action_confirm()
                    _logger.info(f"Estado después de confirmar: {picking.state}")

                if picking.state == 'confirmed':
                    _logger.info(f"Intentando asignar productos al picking: {picking.name}")
                    picking.action_assign()  # Reservar productos automáticamente
                    _logger.info(f"Estado después de intentar asignar: {picking.state}")
                    reserved_quantities = sum(
                        line.reserved_availability for line in picking.move_ids
                    )
                    demanded_quantities = sum(
                        line.product_uom_qty for line in picking.move_ids
                    )
                    _logger.info(
                        f"Picking {picking.name}: {reserved_quantities} de {demanded_quantities} productos reservados."
                    )

                    if picking.state == 'assigned':
                        _logger.info(f"Intentando marcar como entregado el picking: {picking.name}")
                        picking._action_done()
                        _logger.info(f"Estado después de marcar como entregado: {picking.state}")
                    else:
                        _logger.warning(
                            f"No se pudo marcar como entregado el picking {picking.name} porque no está asignado."
                        )
                else:
                    _logger.warning(
                        f"El picking {picking.name} no está en estado asignado o confirmado. Estado actual: {picking.state}"
                    )

                # Validar si el picking realmente está en estado "done"
                if picking.state == 'done':
                    _logger.info(f"Picking {picking.name} correctamente entregado.")
                else:
                    _logger.error(
                        f"Picking {picking.name} aún no está en estado 'done'. Estado actual: {picking.state}."
                    )
            else:
                _logger.warning(f"El picking {picking.name} ya está en estado '{picking.state}'. No se procesará.")

        _logger.info(f"Finalización de la confirmación de entrega para la orden de venta: {picking_origin}")
        return True
        
    def sync_order(self, import_line_id):      
        start_time = datetime.today()

        # Logica para crear productos
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Bearer {import_line_id.instance_id.access_token}'}
        order_ids = import_line_id.description.split(",")

        log_order_id = self.env['vex.meli.logs'].create({'action_type': 'Order', 'vex_restapi_list_id': self.env.ref('odoo-mercadolibre.meli_action_orders').id})
        document_type_general_id = self.env['l10n_latam.identification.type'].search([('name','=', 'VAT')])
        correct_counter=0
        exists_counter = 0
        for order_id in order_ids:
            log_order_id = self.env['vex.meli.logs'].create({'action_type': 'Order', 'vex_restapi_list_id': self.env.ref('odoo-mercadolibre.meli_action_orders').id})
            state = True
            msg = ""
            sale_order_exist = self.env['sale.order'].search([('meli_code', '=', order_id),('instance_id', '=', import_line_id.instance_id.id)], limit=1)
            if len(sale_order_exist) != 0:
                msg = "La orden ya existe"
                _logger.info(msg)

                state = True       
                log_order_id.write({'state': 'done' if state else 'error', 'start_date': start_time,'end_date': datetime.today(), 'description': msg })    
                correct_counter +=1    
                exists_counter += 1                                           
                if sale_order_exist and sale_order_exist.order_status == 'Pending':
                    _logger.info("La orden es PENDIENTE corriendo codigo de actualizacion de orden en caso de ser necesario")
                else:
                    continue
            url_order = f"https://api.mercadolibre.com/orders/{order_id}"
            response_item = requests.get(url_order, headers=headers)
            if response_item.status_code == 200 or response_item.status_code == 206:
                if response_item.status_code == 206:
                    missing_fields = response_item.headers.get('X-Content-Missing', '')
                    _logger.info("Se han recibido datos parciales, pero suficientes para hacer la orden. Campos faltantes: %s", missing_fields)
                json_order = json.loads(response_item.text)
                meli_shipment_id = ""
                meli_shipment_status= ""
                meli_shipment_type = ""     

                if json_order['shipping']['id'] != None:
                    url_shipment = f"https://api.mercadolibre.com/shipments/{json_order['shipping']['id']}"
                    response_shipment = requests.get(url_shipment, headers=headers)
                    if response_shipment.status_code == 200:
                        json_shipment = json.loads(response_shipment.text)
                        meli_shipment_id = json_shipment['id']
                        meli_shipment_type= json_shipment['logistic_type']  if 'logistic_type' in json_shipment else ""
                        meli_shipment_status = json_shipment['status'] 
                else:
                    meli_shipment_status = "Not Delivered"
                partner_exist = False
                json_order_dos = json.loads(response_item.text)

                buyer_info = json_order_dos.get("buyer", {})
                buyer_id = buyer_info.get("id", None)
                buyer_nickname = buyer_info.get("nickname", "")
                buyer_first_name = buyer_info.get("first_name", "")
                buyer_last_name = buyer_info.get("last_name", "")
                partner_exist = self.env["res.partner"].search([('nickname','=', buyer_nickname),('instance_id', '=', import_line_id.instance_id.id)],limit=1)   
                if response_item.status_code == 206 and buyer_nickname == "":
                    _logger.info("Iniciando logica para traer nickname")
                    if not buyer_id:
                        _logger.info("No tenemos ni el id del usuario, deberiamos agregar id 'Cuenta_Eliminada' ")
                        continue
                    buyer_data = f"https://api.mercadolibre.com/users/{buyer_id}"
                    buyer_response = requests.get(buyer_data)
                    if buyer_response.status_code == 200:
                        buyer_info = buyer_response.json()  # Parsear la respuesta a JSON
                        buyer_nickname = buyer_info.get("nickname", "")  # Obtener el nickname o asignar un valor predeterminado
                        if buyer_nickname == "":
                            _logger.error("Fatal error no nicnkname en peticion")
                            continue
                        if buyer_first_name == "":
                            _logger.info("Usuario desactivo su cuenta dando nombre que diga esto: Deactivated Account")
                            buyer_first_name = "Deactivated Account"
                        _logger.info(f"El nickname del comprador con ID {buyer_id} es: {buyer_nickname}")
                    else:
                        _logger.warning(f"No se pudo obtener el nickname del usuario {buyer_id}. Código de estado: {buyer_response.status_code}")
                        continue
                if len(partner_exist) != 0:
                    _logger.info(f"NICKNAME ENCONTRADO --> {buyer_nickname} orden {order_id}")
                if len(partner_exist) == 0 : #No existe el cliente de la orden, entonces creando
                    try:
                        obj_order = {
                            "name": f"{buyer_first_name} {buyer_last_name}",
                            "nickname": buyer_nickname,
                            "l10n_latam_identification_type_id": 1,
                            "server_meli": True,
                            "meli_user_id": buyer_id,
                            "instance_id": import_line_id.instance_id.id
                        }
                        partner_exist = self.env['res.partner'].create(obj_order)
                        if partner_exist:
                             _logger.info(f"Creado nuevo partner para orden {json_order['id']} nombre comprador {buyer_nickname}")                           
                    except Exception as ex:
                        _logger.error(f"Error al crear cliente: {ex}")
                sale_line_ids = []
                if len(json_order['order_items']) > 1:
                    _logger.info("Multiples productos")
                for item in json_order['order_items']:
                    product_tmpl_id = self.env['product.template'].search([('default_code', '=', item['item']['id']), ('active','=',True),('instance_id', '=', import_line_id.instance_id.id)], limit=1)                                
                    product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_id.id), ('active','=',True)])                                
                    if len(product_tmpl_id)==0:
                        _logger.info(f"El producto: {item['item']['id']} no se encontro, intentando recuperar")
                        import_line_temp = self.env['vex.import_line'].create({
                        'stock_import' : True,
                        'images_import' : True,
                        'description': f"{item['item']['id']}",  
                        'instance_id': import_line_id.instance_id.id,
                        'status': 'pending'                       
                         })
                        self.sync_product(import_line_temp)
                        product_tmpl_id = self.env['product.template'].search([('default_code', '=', item['item']['id']), ('active','=',True),('instance_id', '=', import_line_id.instance_id.id)], limit=1)                                
                        product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_id.id), ('active','=',True)])
                        if len(product_tmpl_id)==0:
                            default_code='GENERIC-001'
                            name='Producto Genérico'
                            product_tmpl = self.env['product.template'].search([('default_code', '=', default_code),('instance_id', '=', import_line_id.instance_id.id)], limit=1)
                            if not product_tmpl:
                                product_tmpl = self.env['product.template'].create({
                                    'name': name,
                                    'default_code': default_code,
                                    'type': 'product',
                                    'sale_ok': True,
                                    'purchase_ok': False,
                                    'list_price': 0.0,
                                    'instance_id': import_line_id.instance_id.id
                                })
                            product = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl.id)], limit=1)
                            if not product:
                                product = self.env['product.product'].create({
                                    'product_tmpl_id': product_tmpl.id,
                                    'default_code': default_code
                                })
                            product_tmpl_id =  self.env['product.template'].search([('default_code', '=', default_code),('instance_id', '=', import_line_id.instance_id.id)], limit=1)                             
                            product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl.id)], limit=1)
                            if len(product_tmpl_id)==0:
                                _logger.error("Aun no se pudo crear el producto terminando todo FATAL ERROR")
                                msg = f"Order wasn't created because {item['item']['id']} does not exist"
                                _logger.warning(msg)
                                state = False    
                                log_order_id.write({'state': 'done' if state else 'error', 'start_date': start_time,'end_date': datetime.today(), 'description': msg })                                                      
                                break
                            else:
                                _logger.info("PRODUCTO GENERICO USANDOSE EXITOSAMENTE")
                        else:
                            _logger.info(f"Producto {item['item']['id']} recuperado exitosamente")                        
                    tax_value = 0
                    for tax in product_tmpl_id.taxes_id:
                        if tax.amount != 0:
                            tax_value += 1/tax.amount    
                    if product_tmpl_id.is_package:
                        for product_tmpl_item_id in product_tmpl_id.product_unit_ids:
                            product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_item_id.product_id.id), ('active','=',True)])                                
                            obj_line = {
                                'product_id':product_id.id,
                                'product_template_id': product_tmpl_item_id.product_id.id,
                                'name': '[PACK] '+product_tmpl_id.name,
                                'product_uom_qty': item['quantity']*product_tmpl_item_id.quantity,
                                'price_unit': item['unit_price'],
                                'tax_id': [(5, 0, 0)],
                                'display_type': False
                            }   
                            sale_line_ids.append((0,0,obj_line))     
                    else:                                
                        obj_line = {
                            'product_id':product_id.id,
                            'product_template_id': product_tmpl_id.id,
                            'name': product_tmpl_id.name,
                            'product_uom_qty': item['quantity'],
                            'price_unit': item['unit_price'],
                            'tax_id': [(5, 0, 0)],
                            'display_type': False
                        }    
                        sale_line_ids.append((0,0,obj_line))
                if not state:
                    log_order_id.write({'state': 'done' if state else 'error', 'start_date': start_time,'end_date': datetime.today(), 'description': msg })
                    continue
                time_data = json_order['date_created']
                date_order = datetime.strptime(time_data, '%Y-%m-%dT%H:%M:%S.%f%z')
                formatted_time = date_order.strftime('%Y-%m-%d %H:%M:%S')
                total_shipping_cost = 0.00
                market_place_fee = 0.00
                order_is_closed = False
                contador_aprovados = 0
                contador_charged_back = 0
                for payment in json_order['payments']:
                    if payment.get('status') == 'approved':                    
                        contador_aprovados += 1
                        total_shipping_cost += payment.get('shipping_cost', 0.00)  # Sumar el costo de envío de cada pago
                        market_place_fee += payment.get('marketplace_fee', 0.00)  # Sumar el costo de envío de cada pago
                    elif payment.get('status') == 'charged_back' and  payment.get('status_detail') == 'reimbursed':   
                        contador_charged_back += 1
                tags = json_order['tags']
                tags_string = ','.join(json_order['tags'])
                order_status = "Unresolved"
                if contador_aprovados >= 1 and 'paid' in tags and 'delivered' in tags and json_order['status'] == 'paid':
                    order_status = "Completada"
                    order_is_closed = True
                elif json_order['status'] == 'cancelled' :
                    order_status = "Canceled"
                elif contador_aprovados >= 1 and 'paid' in tags and "not_delivered" in tags and json_order['status'] == 'paid':
                    order_status = "Pending"
                elif json_order['status'] == 'partially_refunded':                    
                    order_status = "Partially Refunded"                    
                elif contador_aprovados == 0 and contador_charged_back >=1:
                    order_status = 'Reimbursed' 
                elif contador_aprovados == 0:
                    order_status = "No Pagada"
                if json_order['fulfilled'] and contador_aprovados >= 1 and json_order['status'] == 'paid' and 'no_shipping' in tags and not json_order['pack_id']:
                    _logger.info("Orden especial de entrega digital")
                    order_status = "Completada"
                _logger.info(f"Tiene una categorizacion de {order_status} y {json_order['status'],}  Con los tags -> {tags}   Con pagos aproved-> {contador_aprovados}")
                #_logger.info(f"COMMENT {json_order.get('comment', 'no existe')}")
                obj_sale ={
                    'meli_code': json_order['id'],
                    'partner_id': partner_exist.id,  # ID del cliente
                    'date_order': formatted_time,  # Fecha de la orden
                    'state': 'sale',  # Estado inicial de la orden
                    'server_meli': True,  # Estado inicial de la orden
                    'shipping_id': meli_shipment_id,  # Estado inicial de la orden
                    'shipping_type': meli_shipment_type,  # Estado inicial de la orden
                    'shipping_status': meli_shipment_status,  # Estado inicial de la orden
                    'listing_type_id': item['listing_type_id'],
                    'order_line':sale_line_ids,
                    'meli_order_comment': json_order.get('comment', ''),
                    'fulfilled': json_order['fulfilled'],
                    'buying_mode': json_order['buying_mode'],
                    'pack_id': json_order['pack_id'],
                    'payment_method_id': json_order['payments'][0]['payment_method_id'],
                    'operation_type':  json_order['payments'][0]['operation_type'],
                    'payment_type': json_order['payments'][0]['payment_type'],
                    'payment_status': json_order['status'],
                    'payment_status_detail': json_order['payments'][0]['status_detail'],
                    'total_paid_amount': json_order['paid_amount'], 
                    'marketplace_fee': market_place_fee,
                    'shipping_cost' : total_shipping_cost,                    
                    'meli_payment_code': json_order['payments'][0]['id'],
                    'meli_collector_id':  json_order['payments'][0]['collector']['id'],
                    'meli_card_id': json_order['payments'][0]['card_id'],
                    'instance_id':import_line_id.instance_id.id,
                    'tags' : tags_string,
                    'order_status' : order_status,
                    'order_is_closed' : order_is_closed,
                    'meli_channel': json_order.get('context', {}).get('channel', 'unknown'),
                    'meli_flows': ', '.join(json_order.get('context', {}).get('flows', [])),
                }                           
                if total_shipping_cost > 0 or market_place_fee > 0 :                    
                    _logger.info(f"Shiping = {total_shipping_cost} ML_FEE = {market_place_fee}  Total = {json_order['paid_amount']}  Comisiones {total_shipping_cost+market_place_fee} Con el estatus {json_order['status']}")
                number_of_payments = len(json_order.get('payments', []))     
                if number_of_payments >= 2:
                    _logger.info("Hay más de dos pagos en esta orden.") 
                sale_order_exist = self.env['sale.order'].search([('meli_code', '=', order_id),('instance_id', '=', import_line_id.instance_id.id)], limit=1)
                if sale_order_exist:
                    sale_order_exist.write({'marketplace_fee': market_place_fee}) #IMPORTANTE LINEA CON BUG, EVITAR 2 WEBHOOKS ACCESANDO MISMALINEA MISMO TIEMPO FIX
                    sale_order_exist.write({'shipping_cost': total_shipping_cost})
                    order_status_antigua = sale_order_exist.order_status
                    order_status_Actual = order_status
                    if order_status_antigua != order_status_Actual:
                        _logger.info(f"Actualizando order status de {sale_order_exist.order_status} a {order_status}")
                        sale_order_exist.write({'order_status': order_status})
                        _logger.info(f"Actualizando TAGS de {sale_order_exist.tags} a {tags_string}")
                        sale_order_exist.write({'tags': tags_string})
                        _logger.info(f"Actualizando STATUS de {sale_order_exist.payment_status} a {json_order['status']}")
                        sale_order_exist.write({'payment_status': json_order['status']})
                        _logger.info("ACTUALIZACION TERMINADA")
                        if order_status_antigua == 'Pending' and order_status_Actual == 'Completada':
                            _logger.info("Orden actualizada de pendiente a completada...ahora si, completando factura")
                            for picking in sale_order_exist.picking_ids:
                                _logger.info(f"Iniciando asignación de productos para la transferencia {picking.id}")
                                picking.action_assign()  # Intentar asignar productos
                                if picking.state == 'confirmed':  # Verificar si falta stock
                                    _logger.warning(f"No hay suficiente stock para la transferencia {picking.id}. Ajustando stock.")
                                    for move in picking.move_ids_without_package:  # Iterar sobre los movimientos
                                        product = move.product_id
                                        qty_required = move.product_uom_qty
                                        location = move.location_id
                                        qty_available = self.env['stock.quant']._get_available_quantity(product, location)
                                        if qty_available < qty_required:  # Si falta stock
                                            qty_to_add = qty_required - qty_available
                                            self.env['stock.quant'].create({
                                                'product_id': product.id,
                                                'location_id': location.id,
                                                'quantity': qty_to_add,
                                            })
                                            _logger.info(f"Stock ajustado: {qty_to_add} unidades de producto {product.id} en la ubicación {location.id}.")
                                    picking.action_assign()  # Reasignar productos después de ajustar el stock
                                    _logger.info(f"Stock ajustado y asignado para la transferencia {picking.id}.")

                                picking.button_validate()  # Validar entrega
                                _logger.info(f"Transferencia {picking.id} validada.")
                            try:
                                self._create_and_post_invoice(sale_order_exist, json_order, import_line_id)
                            except Exception as e:
                                _logger.warning(f"Error al crear y publicar la factura para la orden {sale_order_exist.id}: {str(e)}")
                        if order_status_antigua == 'Pending' and order_status_Actual == 'Canceled':
                            _logger.info("Orden paso de pendiente a cancelada, cancelando comisiones")
                            sale_order_exist.write({'shipping_cost': 0})
                            sale_order_exist.write({'marketplace_fee': 0})
                        continue
                    continue
                else:
                    new_order = self.env['sale.order'].create(obj_sale)
                    if new_order.order_status == "Completada":
                        for picking in new_order.picking_ids:
                            _logger.info(f"Iniciando asignación de productos para la transferencia {picking.id}")
                            picking.action_assign()  # Intentar asignar productos
                            if picking.state == 'confirmed':  # Verificar si falta stock
                                _logger.warning(f"No hay suficiente stock para la transferencia {picking.id}. Ajustando stock.")
                                for move in picking.move_ids_without_package:  # Iterar sobre los movimientos
                                    product = move.product_id
                                    qty_required = move.product_uom_qty
                                    location = move.location_id
                                    qty_available = self.env['stock.quant']._get_available_quantity(product, location)
                                    if qty_available < qty_required:  # Si falta stock
                                        qty_to_add = qty_required - qty_available
                                        self.env['stock.quant'].create({
                                            'product_id': product.id,
                                            'location_id': location.id,
                                            'quantity': qty_to_add,
                                        })
                                        _logger.info(f"Stock ajustado: {qty_to_add} unidades de producto {product.id} en la ubicación {location.id}.")
                                picking.action_assign()  # Reasignar productos después de ajustar el stock
                                _logger.info(f"Stock ajustado y asignado para la transferencia {picking.id}.")
                            picking.button_validate()  # Validar entrega
                            _logger.info(f"Transferencia {picking.id} validada.")
                if new_order:
                    msg="Orden creada con exito"
                    state=True
                    log_order_id.write({'state': 'done' if state else 'error', 'start_date': start_time,'end_date': datetime.today(), 'description': msg })                                                   
                    _logger.info("Se creo")           
                    _logger.info("Logica para la entrega del producto")
                    if import_line_id.instance_id.generate_invoice_imported_orders and new_order.order_status == "Completada" :  ##SOLO HACER FACTURAS DE PAID ONES 
                        # Use the created order directly
                        order = new_order
                        self._create_and_post_invoice(order, json_order,import_line_id)
                    else:
                        _logger.info("Automatic invoices disabled  u orden no apta")
                correct_counter +=1
            else:
                msg = "Error en el request order"
                _logger.info(f"272183 {response_item.text}")
                state = False
                log_order_id.write({'state': 'done' if state else 'error', 'start_date': start_time,'end_date': datetime.today(), 'description': msg })
                _logger.info(msg)
        end_time = datetime.today()
        if correct_counter == len(order_ids):
            import_line_id.write({'start_date': start_time,'end_date': end_time,'checks_indicator':f'{correct_counter}/{len(order_ids)}','status': 'done'})
        elif correct_counter < len(order_ids) and correct_counter != 0:
            import_line_id.write({'start_date': start_time,'end_date': end_time,'checks_indicator':f'{correct_counter}/{len(order_ids)}','status': 'obs'})
        elif correct_counter == 0:
            import_line_id.write({'start_date': start_time,'end_date': end_time,'checks_indicator':f'{correct_counter}/{len(order_ids)}','status': 'error'})
        if exists_counter == 20:
            return "pass"

    def get_data_from_api(self, uri, header):
        """
        Función que nos permite consumir un API RestFUL y que nos devuelve la respuesta

        Attributes:
            uri (str): Endpoint donde se va a consumir
            header (str): Cabecera
        """
        response = requests.get(uri, headers=header)

        json_response = False

        if response.status_code != 204:
            json_response = json.loads(response.text)

       #print("response status - order: ", response.status_code)        
       # print("json_response: ", json_response)

        return json_response