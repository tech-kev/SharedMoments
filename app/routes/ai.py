from flask import Blueprint, Response, request, stream_with_context, jsonify, g
from app.routes.auth import jwt_required
from app.ai import stream_ai_response
from app.translation import _

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/api/v2/ai/enhance', methods=['POST'])
@jwt_required
def enhance_text():
    # Check if user has any Create or Update permission for any list
    user_perms = getattr(g, 'user_permissions', set())
    has_any = any(p.startswith('Create ') or p.startswith('Update ') for p in user_perms)
    if not has_any:
        return jsonify({
            'status': 'error',
            'message': _('Insufficient permissions'),
            'data': {'error_code': 403}
        }), 403

    text = request.form.get('text', '').strip()
    if not text:
        return Response("data: Error: No text provided\n\ndata: [DONE]\n\n",
                        mimetype='text/event-stream')

    return Response(
        stream_with_context(stream_ai_response(text)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )
