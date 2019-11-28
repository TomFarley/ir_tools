PRO calibration_error_tint, ps=ps

;select the range of pixels to average over
range=[120,160,100,160]

;temps to check
temps=['30','40','50','60','70','80','100','150','200','250','300','350','450']
tint=['5','10','30','50','70','100','250','500','700']

;calculate the error on the conversion against the blackbody temp

;ifrst ircam 0101 50 mm filtered
folder='IRcam_0101_50mm_20181121'
tcalc_0101_filt=make_array(n_elements(tint), n_elements(temps))
error_0101_filt=make_array(n_elements(tint), n_elements(temps))
bb_counts=make_array(n_elements(tint), n_elements(temps))
bg_counts=make_array(n_elements(tint), n_elements(temps))
img_counts=make_array(n_elements(tint), n_elements(temps))

for i=0, n_elements(temps)-1 do begin
	for j=0, n_elements(tint)-1 do begin
		
		tmp=raw_to_temp_tint(folder, tint[j], temps[i], [7.7,9.4], range)
		tcalc_0101_filt[j,i]=tmp.avg
		error_0101_filt[j,i]=tcalc_0101_filt[j,i]-temps[i]
		bb_counts[j,i]=tmp.bb_avg
		bg_counts[j,i]=tmp.bg_avg
		img_counts[j,i]=tmp.img_avg
	endfor
endfor

;plot an example of a calibrated image
;tmp=raw_to_temp(folder, '50', '50', [7.7,9.4], range)
tmp=raw_to_temp(folder, '500', '40', [7.7,9.4], range)

if keyword_set(ps) then begin
	atpsopen, filename='calib_test_image.eps'
	setup_ps
endif else window, 0

cp_shade, tmp.tpro, /show, /iso, ztitle='Temperature (!uo!nC)' 

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='calib_test_profile.eps'
	setup_ps
endif else window, 1

plot, tmp.tpro[*,150], $
	position=[0.15,0.15,0.68,0.9], $
	xtitle='Pixel (arb.)', $
	ytitle='Temperature (!uo!nC!n)', xr=[0,320], xs=1

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='calibration_error_0101.eps'
	setup_ps
endif else window, 3 

cols=[truecolor(), truecolor('firebrick'), $
		truecolor('royalblue'), truecolor('limegreen'), $
		truecolor('gold'), truecolor('purple'), $
		truecolor('orange'), truecolor('fuchsia'), $
		truecolor('cyan')]

plot, [0,450], [0,30], /nodata, $
	xtitle='Temperature (!uo!nC)', $
	ytitle='Error (%)', $
	position=[0.15,0.15,0.68,0.9]

xyouts, 0.15,0.905, 'IRcam 0101 50 mm', /normal, charsize=1.0

for i=0, n_elements(tint)-1 do begin

	;remove the saturated points
	loc=where(tcalc_0101_filt[i,*] gt 0 and finite(error_0101_filt[i,*]))

	if loc[0] ne -1 then begin
		oplot, temps, $
			(abs(error_0101_filt[i,loc])/temps)*100., $
			col=cols[i]
	endif
endfor

tint_str=string(tint[0:i-1], format='(i4)')
psym=make_array(n_elements(tint_str))
psym[*]=8
legend_, tint_str, col=cols, psym=psym, $
	/top, /right, charsize=0.75

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

;signal to noise
window, 4

plot, [0,500], [0,50], /nodata, $
	xtitle='Temperature (!uo!nC)', $
	ytitle='Signal/Noise'

for i=0, n_elements(tint)-1 do begin

	;remove the saturated points
	loc=where(tcalc_0101_filt[i,*] gt 0)

	if loc[0] ne -1 then begin
		oplot, temps, $
			img_counts[i,*]/sqrt(bg_counts[i,*]), $
			col=cols[i]
	endif
endfor

tint_str=string(tint, format='(i4)')
legend_, tint_str, col=cols, psym=[8,8,8,8,8,8,8,8,8], $
	/top, /right, charsize=0.75

stop

END
