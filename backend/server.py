# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sensor Data Backend")

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.data_buffer: Dict[str, List] = {}
    
    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        self.data_buffer[device_id] = []
        logger.info(f"Device {device_id} connected")
    
    async def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        logger.info(f"Device {device_id} disconnected")
    
    async def broadcast(self, message: dict):
        """Send message to all connected devices"""
        for device_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {device_id}: {e}")
    
    def get_device_status(self):
        """Return status of all connected devices"""
        return {
            device_id: {
                "connected": True,
                "last_data_count": len(self.data_buffer.get(device_id, []))
            }
            for device_id in self.active_connections
        }

manager = ConnectionManager()

# ML Endpoint configuration
# TODO: Update with ML service URL
ML_ENDPOINT = "http://localhost:8001/predict"

async def send_to_ml_endpoint(sensor_data: dict) -> dict:
    """
    Send sensor data to ML endpoint and get prediction
    
    Args:
        sensor_data: Dictionary containing sensor readings
    
    Returns:
        ML prediction response
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                ML_ENDPOINT,
                json=sensor_data
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"ML endpoint request error: {e}")
        return {"error": str(e), "prediction": None}
    except Exception as e:
        logger.error(f"Unexpected ML endpoint error: {e}")
        return {"error": str(e), "prediction": None}

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint for receiving sensor data from devices
    
    Args:
        websocket: WebSocket connection
        device_id: Unique identifier for the sensor device
    """
    await manager.connect(device_id, websocket)
    
    try:
        while True:
            # Receive sensor data from device
            data = await websocket.receive_text()
            sensor_data = json.loads(data)
            
            logger.info(f"Device {device_id}: {sensor_data}")
            
            # Store in buffer
            manager.data_buffer[device_id].append(sensor_data)
            
            # Send to ML endpoint
            ml_result = await send_to_ml_endpoint(sensor_data)
            
            # Enrich response with ML prediction
            response = {
                "device_id": device_id,
                "received_at": datetime.now().isoformat(),
                "sensor_data": sensor_data,
                "ml_prediction": ml_result
            }
            
            # Send prediction back to device
            await websocket.send_json(response)
            logger.info(f"Sent prediction to {device_id}: {response}")
            
    except WebSocketDisconnect:
        await manager.disconnect(device_id)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from {device_id}: {e}")
        await manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"Unexpected error for {device_id}: {e}")
        await manager.disconnect(device_id)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_devices": len(manager.active_connections),
        "devices": manager.get_device_status()
    }

@app.get("/api/device/{device_id}/history")
async def get_device_history(device_id: str, limit: int = 100):
    """Get stored data from a device"""
    if device_id not in manager.data_buffer:
        return JSONResponse(
            status_code=404,
            content={"error": f"Device {device_id} not found"}
        )
    
    data = manager.data_buffer[device_id][-limit:]
    return {
        "device_id": device_id,
        "record_count": len(data),
        "data": data
    }

@app.delete("/api/device/{device_id}/history")
async def clear_device_history(device_id: str):
    """Clear stored data for a device"""
    if device_id in manager.data_buffer:
        manager.data_buffer[device_id] = []
        return {"message": f"History cleared for {device_id}"}
    return JSONResponse(
        status_code=404,
        content={"error": f"Device {device_id} not found"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
