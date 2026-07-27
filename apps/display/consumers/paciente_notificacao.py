from channels.generic.websocket import AsyncWebsocketConsumer


class PacienteNotificacaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.cpf = self.scope["url_route"]["kwargs"]["cpf"]
        self.group_name = f"paciente_{self.cpf}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def paciente_chamado(self, event):
        await self.send_json({
            "tipo": "paciente_chamado",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "sala": event.get("sala", ""),
            "guiche": event.get("guiche", ""),
            "timestamp": event.get("timestamp", ""),
        })

    async def paciente_concluido(self, event):
        await self.send_json({
            "tipo": "paciente_concluido",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "timestamp": event.get("timestamp", ""),
        })

    async def paciente_atendimento(self, event):
        await self.send_json({
            "tipo": "paciente_atendimento",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "sala": event.get("sala", ""),
            "timestamp": event.get("timestamp", ""),
        })

    async def paciente_ausente(self, event):
        await self.send_json({
            "tipo": "paciente_ausente",
            "senha": event.get("senha", ""),
            "nome": event.get("nome", ""),
            "timestamp": event.get("timestamp", ""),
        })
