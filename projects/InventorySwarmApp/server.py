import json
from http.server import HTTPServer, SimpleHTTPRequestHandler

ITEMS = [
    {"id": "item-001", "name": "ESP32-WROOM-32", "qty": 42, "category": "Hardware"},
    {"id": "item-002", "name": "BC547 NPN Transistor", "qty": 250, "category": "Semiconductors"}
]

class InventoryHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/items':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(ITEMS).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == '__main__':
    print('Starting Inventory Server on :8080')
    HTTPServer(('0.0.0.0', 8080), InventoryHandler).serve_forever()
