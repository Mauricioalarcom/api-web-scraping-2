import requests
import boto3
import uuid
import json

def lambda_handler(event, context):
    # URL de la API que devuelve los sismos
    url = "https://ultimosismo.igp.gob.pe/api/sismos"  # Cambia esta URL a la API real, si existe

    # Realizar la solicitud HTTP
    response = requests.get(url)

    # Verificar si la solicitud fue exitosa
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la API de sismos'
        }

    # Obtener los datos de la respuesta JSON
    sismos_data = response.json()

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('SismosReportados')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'id': each['id']})

    # Insertar los nuevos datos
    for sismo in sismos_data[:10]:  # Limitar a los primeros 10 sismos
        sismo['id'] = str(uuid.uuid4())  # Generar un ID único para cada entrada
        table.put_item(Item=sismo)

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': json.dumps(sismos_data[:10])  # Devolver los primeros 10 sismos
    }
