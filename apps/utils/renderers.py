from rest_framework.renderers import JSONRenderer


class ResponseRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        if isinstance(data, dict) and data.get('success') is False:
            return super().render(data, accepted_media_type, renderer_context)

        wrapped = {
            "data": data,
            "error": None,
            "success": True,
        }

        return super().render(wrapped, accepted_media_type, renderer_context)