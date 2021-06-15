PRO cam_sensitivity, ps=ps

;plot the number of photons produced at a given wavelength vs temperature
;justify why LWIR integration times are always shorter than the equivalent
;long wavelength version.

temps=(((findgen(100)/99.)*430)+20)

lwir_phots=make_array(n_elements(temps))
mwir_phots=make_array(n_elements(temps))

for i=0, n_elements(temps)-1 do begin
	lwir_phots[i]=blackbody_phot(temps[i]+273., [7.7,9.4])
	mwir_phots[i]=blackbody_phot(temps[i]+273., [4.1,5.0])
endfor

plot, temps, mwir_phots, $
	xtitle='!3 Temperature (!uo!nC)', $
	ytitle='Photons', $
	position=[0.15,0.15,0.68,0.9]

oplot, temps, lwir_phots, col=truecolor('firebrick')

legend_, ['MWIR','LWIR'], $
	col=[truecolor(), truecolor('firebrick')], $
	/top, /left, charsize=1.0, psym=[8,8]

stop

END
