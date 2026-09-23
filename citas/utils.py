from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes


def get_webpay_transaction():
    # credenciales de prueba que transbank publica para todos los
    # desarrolladores, sirven para probar pagos en el ambiente de test
    options = WebpayOptions(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
        IntegrationType.TEST,
    )
    return Transaction(options)
