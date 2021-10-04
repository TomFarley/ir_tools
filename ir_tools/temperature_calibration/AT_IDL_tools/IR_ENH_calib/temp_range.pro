PRO temp_range, ps=ps

;determine what the temperature range should be for the calibration

;400kA ohmic 28866
;air = 266 us; ait= 134 us

temp400u=getdata('ait_temperature_osp', 28866)
temp400l=getdata('air_temperature_osp', 28866)

tr=[0.2,0.4]

sel400u=where(temp400u.time gt tr[0] and temp400u.time lt tr[1])
sel400l=where(temp400l.time gt tr[0] and temp400l.time lt tr[1])

data_u=temp400u.data[sel400u]
data_l=temp400l.data[sel400l]

if keyword_set(ps) then begin
	atpsopen, filename='temperature_ranges.eps'
	setup_ps
endif else window, 0

histogram_at5, data_u, max=150, min=20, bins=5, /line, $
	xtitle='Temperature (!uo!nC)', $
	ytitle='Frequency per bin', $
	position=[0.15,0.15,0.68,0.9], /normal, yr=[0,1]
histogram_at5, data_l, max=30, min=25, bins=1, /line, /over, col=truecolor('red'), /normal

;====================================================
;29210 H mode inter-ELM, 2 beam
temp900u=getdata('ait_temperature_osp', 29210)
temp900l=getdata('air_temperature_osp', 29210)

tlmode=[0.2,0.25]
tinter=[0.272,0.3]

sel900u_l=where(temp900u.time gt tlmode[0] and temp900u.time lt tlmode[1])
sel900u_h=where(temp900u.time gt tinter[0] and temp900u.time lt tinter[1])

data_900lmode=temp900u.data[sel900u_l]
data_900inter=temp900u.data[sel900u_h]

histogram_at5, data_900lmode, max=150, min=100, bins=5, /line, /over, col=truecolor('limegreen'), /normal
histogram_at5, data_900inter, max=150, min=100, bins=5, /line, /over, col=truecolor('gold'), /normal

legend_, ['400 kA lower', '400 kA upper', $
		'900 kA L mode', '900 kA inter-ELM'], $
		/top, /right, charsize=1.0, psym=[8,8,8,8], $
	col=[truecolor('royalblue'), truecolor('red'), $
			truecolor('limegreen'), truecolor('gold')]

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

;=======================================================
;integration times

;extracted the integration times used for the AIR and AIT data in M9 H modes
;from the FM filament database IR spreadsheet
;Make some histos

tmp=read_ascii('tint_m9_hmode.csv', delimter=',', data_start=1)
tint_air=reform(tmp.field1[0,*])
tint_ait=reform(tmp.field1[1,*])

if keyword_set(ps) then begin
	atpsopen, filename='tint_mast.eps'
	setup_ps
endif else window, 1

histogram_at5, tint_air, max=500, min=0, bins=10, /line, $
	position=[0.15,0.15,0.68,0.9], $
	xtitle='Integration time (us)', $
	ytitle='Frequency per bin', /normal, yr=[0,1.0]

histogram_at5, tint_ait, max=250, min=0, bins=10, /line, col=truecolor('red'), /over, /normal

legend_, ['Medium wave IR', 'Long wave IR'], $
	col=[truecolor('royalblue'), truecolor('red')], $
	/top, /right, charsize=1.0, psym=[8,8]

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

stop

END
