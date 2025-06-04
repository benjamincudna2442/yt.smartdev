import json
from flask import Flask, request, jsonify, send_file
from datetime import datetime
import yt_dlp
import os
from uuid import uuid4

app = Flask(__name__)

def get_video_info(url):
    # Use /tmp for cookies in Vercel environment
    cookie_path = '/tmp/cookies.txt'
    ydl_opts = {
        'format': 'all',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'cookiefile': cookie_path if os.path.exists(cookie_path) else None,  # Use cookies only if present
        'noplaylist': True,
        'simulate': True,
        'force_generic_extractor': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'getcomments': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'ios', 'mweb', 'tv'],
                'include_ads': False,
            }
        },
        'merge_output_format': None,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            video_info = {
                'id': info.get('id', ''),
                'title': info.get('title', ''),
                'author': info.get('uploader', '') or info.get('channel', '') or '',
                'thumbnail': info.get('thumbnail', '') or next((t['url'] for t in info.get('thumbnails', []) if t.get('url')), ''),
                'duration': info.get('duration', 0),
                'source': 'youtube'
            }
            
            available_formats = []
            for fmt in formats:
                if 'sb' in fmt.get('format_id', '') or fmt.get('ext', '') == 'mhtml':
                    continue
                if fmt.get('vcodec', 'none') == 'none' and fmt.get('acodec', 'none') == 'none':
                    continue
                
                file_size = fmt.get('filesize') or fmt.get('filesize_approx')
                format_data = {
                    'format_id': str(fmt.get('format_id', '')),
                    'type': 'video' if fmt.get('vcodec', 'none') != 'none' else 'audio',
                    'extension': fmt.get('ext', ''),
                    'quality': build_quality_string(fmt),
                    'url': fmt.get('url', ''),
                    'bitrate': int(fmt.get('tbr', 0) * 1000) if fmt.get('tbr') else None,
                    'width': fmt.get('width'),
                    'height': fmt.get('height'),
                    'fps': fmt.get('fps'),
                    'mime_type': build_mime_type(fmt),
                    'file_size': convert_size(file_size) if file_size else 'Unknown',
                    'protocol': fmt.get('protocol', ''),
                    'format_note': fmt.get('format_note', '')
                }
                available_formats.append(format_data)
            
            video_formats = sorted(
                [f for f in available_formats if f['type'] == 'video'],
                key=lambda x: (x['height'] or 0, x['bitrate'] or 0), reverse=True
            )
            audio_formats = sorted(
                [f for f in available_formats if f['type'] == 'audio'],
                key=lambda x: (x['bitrate'] or 0), reverse=True
            )
            available_formats = video_formats + audio_formats
            
            response = {
                'api': 'TheSmartDev',
                'api_url': 'https://yt-smartdev.vercel.app',
                'timestamp': datetime.utcnow().isoformat(),
                'video_info': video_info,
                'available_formats': available_formats,
                'request': {
                    'url': url,
                    'format': request.args.get('format'),
                    'quality': request.args.get('quality'),
                    'type': request.args.get('type')
                },
                'api_info': {
                    'name': 'TheSmartDev',
                    'version': '1.0.0',
                    'website': 'https://yt-smartdev.vercel.app',
                    'documentation': 'https://yt-smartdev.vercel.app/docs',
                    'copyright': f'© {datetime.now().year} @TheSmartDev. All rights reserved.'
                }
            }
            return response
    except Exception as e:
        return {
            'error': str(e),
            'api': 'TheSmartDev',
            'api_url': 'https://yt-smartdev.vercel.app',
            'timestamp': datetime.utcnow().isoformat(),
            'request': {
                'url': url,
                'format': request.args.get('format'),
                'quality': request.args.get('quality'),
                'type': request.args.get('type')
            },
            'api_info': {
                'name': 'TheSmartDev',
                'version': '1.0.0',
                'website': 'https://yt-smartdev.vercel.app',
                'documentation': 'https://yt-smartdev.vercel.app/docs',
                'copyright': f'© {datetime.now().year} @TheSmartDev. All rights reserved.'
            }
        }, 500

def build_quality_string(fmt):
    ext = fmt.get('ext', '')
    if fmt.get('vcodec', 'none') != 'none':
        height = fmt.get('height', 'unknown')
        hdr = ' HDR' if 'hdr' in fmt.get('format', '').lower() or fmt.get('dynamic_range') == 'HDR' else ''
        return f"{ext} ({height}p{hdr})"
    else:
        abr = int(fmt.get('abr', 0)) if fmt.get('abr') else 0
        return f"{ext} ({abr}kb/s)"

def build_mime_type(fmt):
    vcodec = fmt.get('vcodec', 'none')
    acodec = fmt.get('acodec', 'none')
    if vcodec != 'none' and acodec != 'none':
        return f"video/{fmt.get('ext', '')}; codecs=\"{vcodec}, {acodec}\""
    elif vcodec != 'none':
        return f"video/{fmt.get('ext', '')}; codecs=\"{vcodec}\""
    else:
        return f"audio/{fmt.get('ext', '')}; codecs=\"{acodec}\""

def convert_size(size_bytes):
    if not size_bytes or size_bytes == 'Unknown':
        return 'Unknown'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

@app.route('/', methods=['GET'])
def home():
    return send_file('status.html')

@app.route('/dl', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({
            'error': 'URL parameter is required',
            'api': 'TheSmartDev',
            'api_url': 'https://yt-smartdev.vercel.app',
            'timestamp': datetime.utcnow().isoformat(),
            'request': {
                'url': url,
                'format': request.args.get('format'),
                'quality': request.args.get('quality'),
                'type': request.args.get('type')
            },
            'api_info': {
                'name': 'TheSmartDev',
                'version': '1.0.0',
                'website': 'https://yt-smartdev.vercel.app',
                'documentation': 'https://yt-smartdev.vercel.app/docs',
                'copyright': f'© {datetime.now().year} @TheSmartDev. All rights reserved.'
            }
        }), 400
    
    # Check for cookies.txt in /tmp
    cookie_path = '/tmp/cookies.txt'
    if not os.path.exists(cookie_path):
        # No error, just proceed without cookies
        pass
    
    response = get_video_info(url)
    if 'error' in response:
        return jsonify(response), 500
    return jsonify(response)

@app.route('/docs', methods=['GET'])
def docs():
    return send_file('status.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
