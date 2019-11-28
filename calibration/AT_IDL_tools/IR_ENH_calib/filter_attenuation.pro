PRO filter_attenuation, ps=ps

;calculate the attenuation of the filter based on the IRcam0102 calibration with and without it at 50 mm focal length

;values extracted from perform_calib manually by searching for the integration time required in the arrange and matching the temperatures between the with and without filter testing

;plot the counts at a given integration time with and without the filter
;calculate the average attenuation seen

temps=[30,50,100,200]
count_no_filter_50us=[143.15,508.21,1963.,6703.8]
count_no_filter_70us=[201.99,713.70,2744.65,9365.14]
count_no_filter_250us=[779.5, 2519.71, !values.f_nan, !values.f_nan] ;saturation

count_filter_50us=[27.67,118.85,469.23,1615.42]
count_filter_70us=[39.90,169.27,661.92,2264.05]
count_filter_250us=[144.82,602.73, !values.f_nan, !values.f_nan]

atten_50us=count_filter_50us/count_no_filter_50us
atten_70us=count_filter_70us/count_no_filter_70us
atten_250us=count_filter_250us/count_no_filter_250us

temps_all=[temps,temps,temps]
atten_all=[atten_50us, atten_70us, atten_250us]
tint_all=[50,50,50,50, 70,70,70,70, 250,250,250,250]

;the ones at temp=30 are low signal on the filtered case so likely noisy
;remove these and average the others
sel=where(temps gt 30)
avg_atten=mean(atten_all[sel], /nan)
std_atten=stddev(atten_all[sel], /nan)

print, avg_atten
print, std_atten

if keyword_set(ps) then begin
	atpsopen, filename='attenuation_0102_filter_temp_counts.eps'
	setup_ps
endif else window, 0

plot, temps, count_no_filter_50us, psym=-8, $
	position=[0.15,0.15,0.68,0.9], $
	xtitle='Temperature (!uo!nC)', $
	ytitle='ADC counts', xr=[0,250]

oplot, temps, count_filter_50us, psym=-4, col=truecolor('firebrick')

legend_, ['No filter', 'Filter'], $
	psym=[8,4], col=[truecolor(), truecolor('firebrick')], $
	/top, /left, charsize=1.2

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='attenuation_0102_filter_att.eps'
	setup_ps
endif else window, 1

plot, temps, count_filter_50us/count_no_filter_50us, psym=8, $
	xtitle='Temperature (!uo!nC)', $
	ytitle='Attenuation (arb.)', $
	position=[0.15,0.15,0.68,0.9], yr=[0,0.3], xr=[0,250]
oplot, temps, count_filter_70us/count_no_filter_70us, psym=4
oplot, temps, count_filter_250us/count_no_filter_250us, psym=5

oplot, !x.crange, [avg_atten, avg_atten], linestyle=2

legend_, ['50 us', '70 us', '250 us'], $
	psym=[8,4,5], /bottom, /left, charsize=1.2

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

stop

END
