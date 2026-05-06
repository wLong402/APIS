# -*- coding: utf-8 -*-
"""Web 管理服务器"""

import os
import sys
from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from connectors import list_connectors  # noqa: E402
from web import jobs as jobs_mod  # noqa: E402
from web import scheduler as sched_mod  # noqa: E402

WEB_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)


@app.after_request
def _no_cache(resp):
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/')
def index():
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/api/connectors')
def api_connectors():
    out = []
    for name, info in list_connectors().items():
        services = []
        seen = set()
        for sname, sinfo in (info.get('services') or {}).items():
            if sname in seen:
                continue
            seen.add(sname)
            label = sinfo.get('name') if isinstance(sinfo, dict) else sname
            services.append({'name': sname, 'label': label})
        services.sort(key=lambda x: x['name'])
        out.append({
            'name': name,
            'display_name': info.get('display_name', name),
            'services': services,
        })
    return jsonify(out)


@app.post('/api/run')
def api_run():
    data = request.get_json(force=True) or {}
    if not data.get('connector') or not data.get('service'):
        return jsonify({'error': 'connector / service 必填'}), 400
    job = jobs_mod.run_job(data, source='manual')
    return jsonify(job)


@app.get('/api/jobs')
def api_jobs():
    return jsonify(jobs_mod.list_jobs(limit=int(request.args.get('limit', 100))))


@app.get('/api/jobs/<job_id>')
def api_job_detail(job_id):
    j = jobs_mod.get_job(job_id)
    if not j:
        return jsonify({'error': 'not found'}), 404
    return jsonify(j)


@app.get('/api/jobs/<job_id>/log')
def api_job_log(job_id):
    offset = int(request.args.get('offset', 0))
    return jsonify(jobs_mod.read_log(job_id, offset))


@app.post('/api/jobs/<job_id>/stop')
def api_job_stop(job_id):
    ok = jobs_mod.stop_job(job_id)
    return jsonify({'ok': ok})


@app.get('/api/schedules')
def api_schedules():
    return jsonify(sched_mod.list_schedules())


@app.post('/api/schedules')
def api_schedules_add():
    data = request.get_json(force=True) or {}
    name = data.get('name')
    payload = data.get('payload') or {}
    trigger = data.get('trigger') or {}
    enabled = bool(data.get('enabled', True))
    if not payload.get('connector') or not payload.get('service'):
        return jsonify({'error': 'payload.connector / service 必填'}), 400
    if trigger.get('type') not in ('daily', 'interval', 'cron'):
        return jsonify({'error': 'trigger.type 必须为 daily/interval/cron'}), 400
    s = sched_mod.add_schedule(name, payload, trigger, enabled)
    return jsonify(s)


@app.put('/api/schedules/<sid>')
def api_schedules_update(sid):
    data = request.get_json(force=True) or {}
    s = sched_mod.update_schedule(sid, **data)
    if not s:
        return jsonify({'error': 'not found'}), 404
    return jsonify(s)


@app.delete('/api/schedules/<sid>')
def api_schedules_delete(sid):
    ok = sched_mod.delete_schedule(sid)
    return jsonify({'ok': ok})


@app.post('/api/schedules/<sid>/toggle')
def api_schedules_toggle(sid):
    s = sched_mod.toggle_schedule(sid)
    if not s:
        return jsonify({'error': 'not found'}), 404
    return jsonify(s)


@app.post('/api/schedules/<sid>/run')
def api_schedules_run(sid):
    j = sched_mod.run_now(sid)
    if not j:
        return jsonify({'error': 'not found'}), 404
    return jsonify(j)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='0.0.0.0')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--debug', action='store_true')
    args = p.parse_args()

    sched_mod.start()
    print(f'Web 控制台已启动: http://localhost:{args.port}')
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False, threaded=True)


if __name__ == '__main__':
    main()
