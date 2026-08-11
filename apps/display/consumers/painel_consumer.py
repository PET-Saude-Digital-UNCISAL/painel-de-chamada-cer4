from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PainelChamadaConsumer(AsyncJsonWebsocketConsumer):
    GROUP_NAME = "painel_chamada"

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def paciente_chamado(self, event):
        await self.send_json({
            "tipo": "paciente_chamado",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "sala": event.get("sala", ""),
            "guiche": event.get("guiche", ""),
            "timestamp": event.get("timestamp", ""),
        })

    async def fila_atualizada(self, event):
        await self.send_json({
            "tipo": "fila_atualizada",
            "fila": event.get("fila", []),
            "timestamp": event.get("timestamp", ""),
        })

    async def painel_config(self, event):
        await self.send_json({
            "tipo": "painel_config",
            "config": event.get("config", {}),
        })
