import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f))
    print(f, {k: v for k, v in d['S'].items() if k in ('cc', 'wn1', 'wp1', 'l1', 'lr', 'wr')}, f"wall {d['wall_s']:.0f}s")
    for r in d['rows']:
        if 'error' in r:
            print(r['name'], 'ERROR', r['error']); continue
        s = f"{r['corner']:3s} {r['temp']:3d} c{r['code']:<2d} {r['vdd']:.2f} {r['block']:4s} f {r['f_a0']/1e6:7.2f} drift {r['f_drift']*100:+.3f}% a0 {r['a0_min']:.2f}-{r['a0_max']:.2f} vg {r['vg']:.3f}"
        if r['block'] != 'none':
            s += (f" | ls {r['ls_min']:.2f}-{r['ls_max']:.2f} duty {r['ls_duty']*100:.1f} tr/tf {r['ls_tr']*1e12:.0f}/{r['ls_tf']*1e12:.0f}ps"
                  f" /4 {r['f_div']/1e6:.2f} ratio {r['div_ratio']:.4f} duty {r['div_duty']*100:.1f} ck {r['ck_min']:.2f}-{r['ck_max']:.2f}"
                  f" P ls {r['p_ls']*1e3:.3f} div {r['p_div']*1e3:.3f} mW")
        print(s, ' '.join(r['warn']))
