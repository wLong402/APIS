# -*- coding: utf-8 -*-
"""Web 管理服务器"""

import os
import sys
from datetime import datetime, timedelta, timedelta
from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from connectors import list_connectors  # noqa: E402
from connectors.wdt.dwd_cleanse import (  # noqa: E402
    DWD_PULL_SERVICE,
    available_dwd_task_options,
)
from web import jobs as jobs_mod  # noqa: E402
from web import scheduler as sched_mod  # noqa: E402

WEB_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

_WDT_FIXED_BY_DAY = {
    'profits_sku',
    'profits_order',
    'profits_live_sku',
    'profits_live_order',
    'profits_live_refund',
}


def _normalize_time_range(payload: dict):
    connector = payload.get('connector')
    service_name = payload.get('service')
    today = datetime.now().strftime('%Y-%m-%d')
    start = payload.get('start')
    end = payload.get('end')
    past_days = payload.get('past_days')
    from common.past_range import resolve_past_amount, compute_past_time_range
    past_amount, past_unit = resolve_past_amount(payload)
    if past_amount is not None:
        return compute_past_time_range(past_amount, past_unit) + (today,)
    if past_days:
        return compute_past_time_range(int(past_days), 'day') + (today,)
    if connector == 'wdt' and service_name in ('sht_recon_detail', 'recon_delivery_detail') and not start and not end:
        return None, None, today
    s = start or today
    e = end or today
    return (
        s if ' ' in str(s) else f'{s} 00:00:00',
        e if ' ' in str(e) else f'{e} 23:59:59',
        today,
    )


def _build_pull_kwargs(payload: dict, limit: int) -> dict:
    return {
        'shop_no': payload.get('shop_no'),
        'page_size': max(1, min(int(limit), 50)),
        'max_workers': 1,
        'classification_name': payload.get('classification_name'),
        'start_config_record_time': payload.get('start_config_record_time'),
        'end_config_record_time': payload.get('end_config_record_time'),
        'is_summary': payload.get('is_summary') or '0',
        'scheme_name': payload.get('scheme_name'),
        'terms_income': payload.get('terms_income'),
        'composite_dim': payload.get('composite_dim'),
        'split_suite': payload.get('split_suite'),
        'cost_type': payload.get('cost_type'),
        'stat_mode': payload.get('stat_mode'),
        'order_way': payload.get('order_way'),
        'display_by_shop': payload.get('display_by_shop'),
        'display_by_date': payload.get('display_by_date'),
        'original_order': payload.get('original_order'),
        'plat_order_nos': payload.get('plat_order_nos'),
        'erp_order_nos': payload.get('erp_order_nos'),
        'shop_nos': payload.get('shop_nos'),
        'spec_no': payload.get('spec_no'),
        'project': payload.get('project'),
        'summary_no': payload.get('summary_no'),
        'expense_item_name': payload.get('expense_item_name'),
        'order_tools': payload.get('order_tools'),
        'warehouse_no': payload.get('warehouse_no'),
        'period_mark': payload.get('period_mark'),
        'reco_status': payload.get('reco_status'),
        'refund_type': payload.get('refund_type'),
        'salesman_name': payload.get('salesman_name'),
        'start_business_time': payload.get('start_business_time'),
        'end_business_time': payload.get('end_business_time'),
        'debug': bool(payload.get('debug')),
    }


def _preview_data(payload: dict, limit: int = 5) -> dict:
    connector = payload.get('connector')
    service_name = payload.get('service')
    if connector not in ('wdt', 'weiban'):
        raise ValueError(f'不支持的连接器: {connector}')
    if connector == 'wdt':
        from connectors.wdt import create_service
        service = create_service(service_name)
    else:
        if service_name == 'external_user':
            from connectors.weiban.services import ExternalUserPullService
            service = ExternalUserPullService()
        elif service_name == 'external_user_detail':
            from connectors.weiban.services import ExternalUserDetailPullService
            service = ExternalUserDetailPullService()
        else:
            raise ValueError(f'不支持的微伴服务: {service_name}')

    start_time, end_time, today = _normalize_time_range(payload)
    kwargs = _build_pull_kwargs(payload, limit)

    if connector == 'weiban':
        data = service._fetch_data('', '', staff_id=payload.get('shop_no'), **kwargs)
    else:
        if service_name == 'profits_live_order':
            start_date = (start_time or f'{today} 00:00:00').split(' ')[0]
            end_date = (end_time or f'{today} 23:59:59').split(' ')[0]
            resp = service.profits_live_order_api.query(
                start_date=start_date,
                end_date=end_date,
                terms_income=str(payload.get('terms_income') or '1'),
                shop_nos=payload.get('shop_nos'),
                order_tools=payload.get('order_tools'),
                cost_type=payload.get('cost_type'),
                debug=False,
            )
            rows = resp.get('data', []) if isinstance(resp, dict) else []
            return {'items': rows[:limit], 'count': len(rows)}
        if service_name == 'profits_live_refund':
            start_date = (start_time or f'{today} 00:00:00').split(' ')[0]
            end_date = (end_time or f'{today} 23:59:59').split(' ')[0]
            resp = service.profits_live_refund_api.query(
                start_date=start_date,
                end_date=end_date,
                terms_income=str(payload.get('terms_income') or '1'),
                stat_mode=str(payload.get('stat_mode') or '1'),
                shop_nos=payload.get('shop_nos'),
                order_tools=payload.get('order_tools'),
                cost_type=payload.get('cost_type'),
                debug=False,
            )
            rows = resp.get('data', []) if isinstance(resp, dict) else []
            return {'items': rows[:limit], 'count': len(rows)}
        if service_name == 'sht_recon_detail':
            start_date = None
            end_date = None
            if start_time:
                start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
            if end_time:
                end_date = end_time.split(' ')[0] if ' ' in end_time else end_time
            preview_note = None
            if start_date is None and end_date is None:
                start_date = end_date = today
                preview_note = '未填起止日期，预览已默认使用当天账期'
            shop_list = None
            if payload.get('shop_nos'):
                shop_list = [x.strip() for x in str(payload['shop_nos']).split(',') if x.strip()]
            elif payload.get('shop_no'):
                shop_list = [str(payload['shop_no']).strip()]
            rs = payload.get('reco_status')
            reco = [x.strip() for x in str(rs).split(',') if x.strip()] if rs else None
            rt = payload.get('refund_type')
            refund = [x.strip() for x in str(rt).split(',') if x.strip()] if rt else None
            resp = service.sht_recon_detail_api.query(
                period_mark=payload.get('period_mark'),
                start_date=start_date,
                end_date=end_date,
                refund_type=refund,
                shop_no=shop_list,
                reco_status=reco,
                debug=False,
            )
            raw = resp.get('data') if isinstance(resp, dict) else None
            if isinstance(raw, list):
                rows = raw
            elif isinstance(raw, dict):
                rows = [raw]
            else:
                rows = []
            out = {
                'items': rows[:limit],
                'count': len(rows),
                'api_result_code': resp.get('resultCode') if isinstance(resp, dict) else None,
                'api_message': (resp.get('message') if isinstance(resp, dict) else None) or '',
                'api_sub_result_code': resp.get('sub_resultCode') if isinstance(resp, dict) else None,
                'api_sub_detail': (resp.get('sub_detail') if isinstance(resp, dict) else None) or '',
            }
            if preview_note:
                out['preview_note'] = preview_note
            return out
        if service_name == 'recon_delivery_detail':
            start_date = None
            end_date = None
            if start_time:
                start_date = start_time.split(' ')[0] if ' ' in start_time else start_time
            if end_time:
                end_date = end_time.split(' ')[0] if ' ' in end_time else end_time
            preview_note = None
            if start_date is None and end_date is None:
                start_date = end_date = today
                preview_note = '未填起止日期，预览已默认使用当天账期'
            shop_list = None
            if payload.get('shop_nos'):
                shop_list = [x.strip() for x in str(payload['shop_nos']).split(',') if x.strip()]
            elif payload.get('shop_no'):
                shop_list = [str(payload['shop_no']).strip()]
            wh = payload.get('warehouse_no')
            warehouse_list = [x.strip() for x in str(wh).split(',') if x.strip()] if wh else None
            sn = payload.get('summary_no')
            summary_list = [x.strip() for x in str(sn).split(',') if x.strip()] if sn else None
            sp = payload.get('spec_no')
            spec_list = [x.strip() for x in str(sp).split(',') if x.strip()] if sp else None
            po = payload.get('plat_order_nos')
            plat_list = [x.strip() for x in str(po).split(',') if x.strip()] if po else None
            rs = payload.get('reco_status')
            reco = [x.strip() for x in str(rs).split(',') if x.strip()] if rs else None
            resp = service.recon_delivery_detail_api.query(
                period_mark=payload.get('period_mark'),
                start_date=start_date,
                end_date=end_date,
                shop_no=shop_list,
                warehouse_no=warehouse_list,
                spec_no=spec_list,
                summary_no=summary_list,
                reco_status=reco,
                plat_order_no=plat_list,
                salesman_name=payload.get('salesman_name'),
                start_business_time=payload.get('start_business_time'),
                end_business_time=payload.get('end_business_time'),
                debug=False,
            )
            raw = resp.get('data') if isinstance(resp, dict) else None
            if isinstance(raw, list):
                rows = raw
            elif isinstance(raw, dict):
                rows = [raw]
            else:
                rows = []
            out = {
                'items': rows[:limit],
                'count': len(rows),
                'api_result_code': resp.get('resultCode') if isinstance(resp, dict) else None,
                'api_message': (resp.get('message') if isinstance(resp, dict) else None) or '',
                'api_sub_result_code': resp.get('sub_resultCode') if isinstance(resp, dict) else None,
                'api_sub_detail': (resp.get('sub_detail') if isinstance(resp, dict) else None) or '',
            }
            if preview_note:
                out['preview_note'] = preview_note
            return out
        if service_name in _WDT_FIXED_BY_DAY or payload.get('by_day'):
            day = payload.get('start') or today
            start_time = f'{day} 00:00:00'
            end_time = f'{day} 23:59:59'
        elif payload.get('interval') and start_time and end_time:
            sec = int(payload.get('interval') or 0)
            if sec > 0:
                dt_start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                dt_end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                seg_end = min(dt_start + timedelta(seconds=sec - 1), dt_end)
                end_time = seg_end.strftime('%Y-%m-%d %H:%M:%S')
        data = service._fetch_data(start_time, end_time, **kwargs)

    if isinstance(data, dict):
        rows = data.get('data') if isinstance(data.get('data'), list) else [data]
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    return {'items': rows[:limit], 'count': len(rows)}


@app.after_request
def _no_cache(resp):
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
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
    tid = str(data.get('dwd_task', '')).strip()
    if tid:
        svc = DWD_PULL_SERVICE.get(tid)
        if not svc:
            return jsonify({'error': f'未知清洗任务: {tid}'}), 400
        data['connector'] = data.get('connector') or 'wdt'
        data['service'] = svc
        data['dwd_task'] = tid
        job = jobs_mod.run_job(data, source='manual')
        return jsonify(job)
    if not data.get('connector') or not data.get('service'):
        return jsonify({'error': 'connector / service 必填'}), 400
    job = jobs_mod.run_job(data, source='manual')
    return jsonify(job)


@app.get('/api/dwd/available')
def api_dwd_available():
    jobs = jobs_mod.list_jobs(limit=int(request.args.get('limit', 500)))
    return jsonify({'tasks': available_dwd_task_options(jobs)})


@app.post('/api/preview')
def api_preview():
    data = request.get_json(force=True) or {}
    if not data.get('connector') or not data.get('service'):
        return jsonify({'error': 'connector / service 必填'}), 400
    limit = int(data.get('limit') or 5)
    try:
        out = _preview_data(data, limit=max(1, min(limit, 20)))
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/jobs')
def api_jobs():
    return jsonify(jobs_mod.list_jobs(limit=int(request.args.get('limit', 100))))


@app.post('/api/jobs/rerun')
def api_job_rerun_post():
    data = request.get_json(force=True) or {}
    job_id = (data.get('from_job_id') or data.get('job_id') or '').strip()
    if not job_id:
        return jsonify({'error': 'from_job_id 必填'}), 400
    j = jobs_mod.resolve_job_for_rerun(job_id)
    if not j:
        return jsonify({'error': 'not found'}), 404
    payload = j.get('payload') or {}
    if not payload.get('connector') or not payload.get('service'):
        return jsonify({'error': '历史任务缺少 connector/service，无法重跑'}), 400
    job = jobs_mod.run_job(payload, source='manual')
    return jsonify(job)


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


@app.get('/api/jobs/<job_id>/log/download')
def api_job_log_download(job_id):
    j = jobs_mod.get_job(job_id)
    if not j or not j.get('log_path') or not os.path.exists(j['log_path']):
        return jsonify({'error': 'not found'}), 404
    log_dir = os.path.dirname(j['log_path'])
    fname = os.path.basename(j['log_path'])
    return send_from_directory(log_dir, fname, as_attachment=True,
                               download_name=f'{job_id}.log')


@app.get('/api/jobs/<job_id>/summary')
def api_job_summary(job_id):
    return jsonify(jobs_mod.summarize_log(job_id))


@app.post('/api/jobs/<job_id>/stop')
def api_job_stop(job_id):
    ok = jobs_mod.stop_job(job_id)
    return jsonify({'ok': ok})


@app.post('/api/jobs/<job_id>/rerun')
def api_job_rerun(job_id):
    j = jobs_mod.resolve_job_for_rerun(job_id)
    if not j:
        return jsonify({'error': 'not found'}), 404
    payload = j.get('payload') or {}
    if not payload.get('connector') or not payload.get('service'):
        return jsonify({'error': '历史任务缺少 connector/service，无法重跑'}), 400
    job = jobs_mod.run_job(payload, source='manual')
    return jsonify(job)


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
