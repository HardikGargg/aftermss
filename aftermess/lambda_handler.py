"""AWS Lambda entry for Function URL / API Gateway. Same FastAPI app as uvicorn."""

from mangum import Mangum

from aftermess.server import get_app

handler = Mangum(get_app(), lifespan="off")
