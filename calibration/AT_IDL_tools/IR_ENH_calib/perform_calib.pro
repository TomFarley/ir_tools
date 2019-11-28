FUNCTION quadratic, x, p
	y=p[0]+(p[1]*x)+(p[2]*x^2)
	return, y
end

FUNCTION linear, x, p
	y=p[0]+(p[1]*x)
	return, y
end

PRO perform_calib, folder, loc, lambda_range, ps=ps, attenuation=attenuation, fits=fits

if undefined(folder) then folder='IRcam_0101_50mm_20181121'

;set up for the MWIR camera
initial_letter=strmid(folder, 0,1)
lens_lett=strmid(folder, 6,1)
if undefined(loc) then loc=[120,160,100,160]
if initial_letter eq 'F' then loc=[140,170,120,150]
if undefined(lambda_range) then lambda_range=[7.7,9.4]
if initial_letter eq 'F' then lambda_range=[4.1,5.0]
if lens_lett eq '5' then loc=[135,165,130,160]

image_loc=loc

;if initial_letter eq 'F' then bckg_photon_level=1e20 $
;	else bckg_photon_level=2e21


;set fit type
mpfitting=0

;attenuation
if not keyword_set(attenuation) then attenuation=1.0 ;add to adjust the ADC counts to account for a filter

;0102 filter ND 0.6; reduces to 0.238 of unfiltered signal or 
;multiply by 1/0.238=4.202 to go from filtered to unfiltered

lambda_range=lambda_range*1e-6 ;in metres

spawn, 'ls ./'+folder, dirs

;the directories will be the temperatures
;just need to convert to number
temps=dirs*1.0

;now want to go through each of the bb files to see what integration times
;exist, and need to do this for each temperature

data=make_array(n_elements(dirs), 15)
tint=make_array(n_elements(dirs), 15)
temp=make_array(n_elements(dirs), 15)
photons=make_array(n_elements(dirs), 15)
bck_data=make_array(n_elements(dirs), 15)
raw_data=make_array(n_elements(dirs), 15)

for i=0, n_elements(dirs)-1 do begin
	spawn, 'ls ./'+folder+'/'+dirs[i]+'/bb*', files

	;make the file list be extracting from the files variable
	file_list=strarr(n_elements(files))
	integration=make_array(n_elements(files))
	for p=0, n_elements(files)-1 do begin
		tmp=strsplit(files[p], '/', /extract)
		file_list[p]=tmp[-1]
		;get the integration times
		tmp2=strsplit(file_list[p], '_', /extract)
		tmp3=strsplit(tmp2[-1], 'u', /extract)
		integration[p]=tmp3[0]*1.0
	endfor

	;now want to read in the background, and the image, subtract and then
	;extract the counts
	for j=0, n_elements(file_list)-1 do begin
		;read in the image and the background files
		fname='./'+folder+'/'+dirs[i]+'/'+file_list[j]

		if initial_letter eq 'I' then begin
			fname_bg='./'+folder+'/'+dirs[i]+'/'+$
				'bg_'+strtrim(string(fix(integration[j])),2)+'us.ASC'
			print, fname_bg
			img=read_ascii(fname)
			bck=read_ascii(fname_bg)
		endif
		if initial_letter eq 'F' then begin
			fname_bg='./'+folder+'/'+dirs[i]+'/'+$
				'bg_'+strtrim(string(fix(integration[j])),2)+'us.asc'
			print, fname_bg
			img=read_ascii(fname, delimiter=' ', data_start=29)
			bck=read_ascii(fname_bg, delimiter=' ', data_start=29)		
		endif
		counts=img.field001-bck.field001

		;extract the region in the BB source area
		region=counts[loc[0]:loc[1], loc[2]:loc[3]]
		bck_region=bck.field001[loc[0]:loc[1], loc[2]:loc[3]]
		raw_region=img.field001[loc[0]:loc[1], loc[2]:loc[3]]

		signal=mean(region)
		backg=mean(bck_region)
		raw=mean(raw_region)

		data[i,j]=signal
		tint[i,j]=integration[j]
		temp[i,j]=temps[i]
		bck_data[i,j]=backg
		raw_data[i,j]=raw
		
		;convert the temperatures into photons and store
		photons[i,j]=blackbody_phot(temp[i,j]+273., lambda_range)

		;cp_shade, counts, /iso, /show
		;oplot, [loc[0], loc[1]], [loc[2], loc[3]], col=truecolor('red')
		;;wait,1

	endfor
	
endfor

;correct for the attenuation of any neutral density filters added in the 
;system
data=data*attenuation

window, 0
psyms=[1,4,5,6,7,8,4,5,6,7,8,1,4,5,6,7,8,1,4,5,6,7,8]
plot, [0,max(tint)], [0,max(data)], /nodata
for i=0, n_elements(dirs)-1 do begin
	oplot, tint[i,*], data[i,*], psym=psyms[i]
endfor

window, 1
integ=[5,10,30,50,70,100,250,500,700,750,1000,1500]
plot, [0,max(temp)], [0,max(data)], /nodata
for i=0, n_elements(integ)-1 do begin
	sel=where(tint eq integ[i])
	if sel[0] ne -1 then oplot, temp[sel], data[sel], psym=psyms[i]
endfor

window, 3
plot, [0,max(photons)], [0,max(data)], /nodata
for i=0, n_elements(integ)-1 do begin
	sel=where(tint eq integ[i])
	if sel[0] ne -1 then oplot, photons[sel], data[sel], psym=psyms[i]
	;print, integ[i]
	;cursor, x, y, /down
endfor

;now process the results of the calibration. First want a plot of temp
;vs counts at each of the integration times used
;then want to plot photons vs counts and perform a fit
if keyword_set(fits) then begin

if keyword_set(ps) then begin
	atpsopen, filename=folder+'.ps'
	setup_ps
	!p.charsize=1.
endif

endif

for i=0, n_elements(integ)-1 do begin
	sel=where(tint eq integ[i])
	if sel[0] ne -1 then begin
	;make a fit to the photon data, try first linear fitting
	yfit=photons[sel]
	xfit=data[sel]
	rawc=raw_data[sel]
	;some points will saturate - remove
	cut_sat=where(rawc lt 14000)
;	fit=ladfit(xfit[cut_sat], yfit[cut_sat])
	
	if cut_sat[0] ne -1 then begin
	
	start=poly_fit(xfit[cut_sat], yfit[cut_sat], 1)

	fit=mpfitfun('linear', xfit[cut_sat], yfit[cut_sat], $
		sqrt(yfit[cut_sat]), start);, perror=err)

	endif else fit=[0,0]	

	xv=(findgen(50)/49.)*14000

	plot, temp[sel], data[sel], psym=8, $
		position=[0.15,0.15,0.45,0.6], $
		xtitle='!3 Temp (!uo!nC)', $
		ytitle='!3 ADC counts', $
		title='!3 '+string(integ[i])+'us'
	
	plot, data[sel],photons[sel],  psym=8, $
		position=[0.6,0.15,0.9,0.6], $
		ytitle='!3 Photon flux', $
		xtitle='!3 ADC counts', /noerase

	oplot, xv, fit[0]+(fit[1]*xv), col=truecolor('firebrick')

	if cut_sat[0] ne -1 then oplot, xfit[cut_sat], yfit[cut_sat], psym=5, col=truecolor('firebrick')

	if keyword_set(ps) then erase

	if not keyword_set(ps) then	wait,1

	;fitted parameters - save the results
	if i eq 0 then begin
		fitted=fit
		t_integration=integ[i]
		error=err
	endif else begin
		fitted=[[fitted], [fit]]
		t_integration=[t_integration, integ[i]]
		error=[[error], [err]]
	endelse
	endif
endfor

if keyword_set(fits) then begin

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

endif

;make a figure for the report - the counts vs. temp adn counts vs photons
;with fit and parameters

if keyword_set(ps) then begin
	atpsopen, filename='temp_vs_count.eps'
	setup_ps
endif

	sel=where(tint eq 50)

	plot, temp[sel], data[sel], psym=8, $
		position=[0.15,0.15,0.68,0.9], $
		xtitle='!3 Temperature (!uo!nC)', $
		ytitle='!3 ADC counts';, $
		;title='!3 '+string(integ[i])+'us'

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename='photon_vs_count.eps'
	setup_ps
endif

	sel=where(tint eq 50)
	sel2=where(integ eq 50)

	plot, data[sel],photons[sel],  psym=8, $
		position=[0.2,0.15,0.73,0.9], $
		ytitle='!3 Photon flux', $
		xtitle='!3 ADC counts'

	oplot, xv, fitted[0,sel2[0]]+fitted[1,sel2[0]]*xv, $
			col=truecolor('firebrick')

	xyouts, 0.23, 0.85, 'phot. = '+$
		string(fitted[0,sel2[0]], format='(e8.2)')+ ' + ('+ $
		string(fitted[1,sel2[0]], format='(e8.2)')+')*Counts', $
		/normal, charsize=1.0

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

;fitted results
;plot the results against 1/integration time and then fit the result to 
;get the calibration curves for the a and b component of the linear
;fit at a given integration time

if keyword_set(ps) then begin
	atpsopen, filename=folder+'a_coeff.eps'
	setup_ps
endif else window, 4

plot, 1./t_integration, fitted[0,*], psym=8, $
	xtitle='!3 1/t!lint!n (us!u-1!n)', $
	ytitle='!3 a coefficient', $
	position=[0.2,0.15,0.73,0.9]
oploterror, 1./t_integration, fitted[0,*], error[0,*], psym=3

xfit=1./t_integration
fit_a=mpfitfun('linear', xfit, fitted[0,*], error[0,*], fitted[*,0]);,$	
					;perror=error_a)
xv=(findgen(100)/99.)*0.5
oplot, xv, fit_a[0]+(fit_a[1]*xv), col=truecolor('red')

xyouts, 0.23, 0.25, '!3 a = ('+ string(fit_a[0], format='(e9.2)')+'!3 ) + '+$
		'!3 ('+string(fit_a[1], format='(e9.2)')+'!3 )(1/t(int))', $
	/normal, charsize=1.5


if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

if keyword_set(ps) then begin
	atpsopen, filename=folder+'b_coeff.eps'
	setup_ps
endif else window, 5

;for the 0101 lwir calib, then the long integration time fits (1/tint small)
;are not good - there is one with very few points (1000us) that gives a poor
;result - maybe remove these points from the fitting?

plot, 1./t_integration, fitted[1,*], psym=8, $
	xtitle='!3 1/t!lint!n (us!u-1!n)', $
	ytitle='!3 b coefficient', $
	position=[0.2,0.15,0.73,0.9]
oploterror, 1./t_integration, fitted[0,*], error[1,*], psym=3

xfit=1./t_integration

if mpfitting eq 1 then begin
er=(fitted[1,*])
fit_b=mpfitfun('linear', xfit, fitted[1,*], er, fitted[*,0]);, $
					;perror=error_b)
endif else fit_b=linfit(xfit, fitted[1,*])

oplot, xv, fit_b[0]+(fit_b[1]*xv), col=truecolor('firebrick')

xyouts, 0.23, 0.85, '!3 b = ('+ string(fit_b[0], format='(e9.2)')+'!3 ) + '+$
		'!3 ('+string(fit_b[1], format='(e9.2)')+'!3 )(1/t(int))', $
	/normal, charsize=1.5

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif

;plot a set of the integration time photon vs adc counts data with the
;fitted params and the final B fit data

ti=[10,30,50,70,100,250,500]

if keyword_set(ps) and keyword_set(fits) then begin

	set_plot, 'ps'
	device, filename=folder+'_allfit.eps', /colo, /encap, bits_per_pixel=8, $
		xsize=7, ysize=10.5, /inches, /portrait
	setup_ps
	!p.charsize=0.75
;	window, 10, xsize=800, ysize=1200

gap=0.075
delta_plot=0.15

	for i=0, n_elements(ti)-1 do begin

		if i mod 2 eq 0 then begin
			inner=0.15
			outer=0.45
;			btm=((0.8-(gap*i/2.))-((i/2.)*0.15))
;			top=((1.0-(gap*i/2.))-((i/2.)*0.15))
			row=i/2.
			top=(0.95-((delta_plot+gap)*row))
			btm=top-delta_plot
		endif
		if i mod 2 eq 1 then begin
			inner=0.65
			outer=0.95
;			btm=((0.8-(gap*(i-1)/2.))-(((i-1)/2.)*0.15))
;			top=((1.0-(gap*(i-1))/2.)-(((i-1)/2.)*0.15))
			row=(i-1)/2.
			top=(0.95-((delta_plot+gap)*row))
			btm=top-delta_plot
		endif

		print, btm

		;select the data
		sel=where(tint eq ti[i])
		selfit=where(t_integration eq ti[i])
		plot, data[sel]/1e3, photons[sel], psym=8, $
			position=[inner,btm,outer,top], $
			title='!3 t(int) = '+string(ti[i], format='(i3)')+' us', $
			/noerase, $
			symsize=0.75, $
			xtitle='!3 ADC counts (x10!u3!n)', $
			ytitle='!3 Photon flux'

		xv=(findgen(50)/49.)*14000

		oplot, xv/1e3, fitted[0,selfit[0]]+(fitted[1,selfit[0]]*xv), $
			col=truecolor('firebrick')

		string_fit='!3 y='+string(fitted[0,selfit[0]], format='(e9.2)')+$
					'!3 +'+$
					string(fitted[1,selfit[0]], format='(e9.2)')

		xyouts, inner+0.001, top-0.025, string_fit, /normal, charsize=0.65

	endfor

	;add a title to the whole plot
	xyouts, 0.35, 0.97, folder, /normal, charsize=1.

	;now plot the B fit
	plot, 1./t_integration, fitted[1,*], psym=8, $
		xtitle='!3 1/t!lint!n (us!u-1!n)', $
		ytitle='!3 b coefficient', $
		position=[0.65,btm,0.95,top], /noerase, $
		title='!3 CALIBRATION COEFF.'
	oploterror, 1./t_integration, fitted[1,*], error[1,*], psym=3

	oplot, xv, fit_b[0]+(fit_b[1]*xv), col=truecolor('royalblue')

	xyouts, 0.65+0.001, top-0.025, $
		'!3 b = ('+ string(fit_b[0], format='(e9.2)')+$
		'!3 ) + '+$
		'!3 ('+string(fit_b[1], format='(e9.2)')+'!3 )(1/t(int))', $
	/normal, charsize=0.65

	device, /close_file
	set_plot, 'X'

	setup_ps, /unset

endif 

;make a version of the B fit plot that expands the small value range - want
;to understand wh ythe LWIR data has poor error at long integration times

window, 7

plot, 1./t_integration, fitted[1,*], psym=8, $
	xtitle='!3 1/t!lint!n (us!u-1!n)', $
	ytitle='!3 b coefficient', $
	position=[0.2,0.15,0.73,0.9], xr=[0,0.014]

oploterror, 1./t_integration, fitted[1,*], error[1,*], psym=3

xfit=1./t_integration

xv=(findgen(100)/99.)*0.5
oplot, xv, fit_b[0]+(fit_b[1]*xv), col=truecolor('red')

xyouts, 0.23, 0.25, '!3 b = ('+ string(fit_b[0], format='(e9.2)')+'!3 ) + '+$
		'!3 ('+string(fit_b[1], format='(e9.2)')+'!3 )(1/t(int))', $
	/normal, charsize=1.5

;normalise the photon counts by the integration time and then plot all the
;tint one one graph

;determine the background offset from the fits to the data at each
;integration time
bckg_photon_level=mean(fitted[0,*])

if keyword_set(ps) then begin
	atpsopen, filename=folder+'calib_all_tintscaled.eps'
	setup_ps
endif else window, 11

col=[truecolor(), truecolor('firebrick'), $
	truecolor('royalblue'), truecolor('limegreen'), $
	truecolor('gold'), truecolor('orange'), $
	truecolor('cyan'), truecolor('purple'), $
	truecolor('gray'), truecolor('fuchsia'), $
	truecolor('olive')]

psym=[8,8,8,4,5,7,8,8,8,8,7]

;scale for plot - need to remove saturated values
vals=photons*tint
locate=where(raw_data lt 14000)

max_plot=max(vals[locate], /nan)

phot=[0]
dat=[0]

plot, [0,10000], [0, max_plot], /nodata, $
	ytitle='!3 Photons (sr!u-1!n m!u-3!n)', $
	xtitle='ADC counts' , $;greek('Delta')+'!3 DL (arb.)', $
	position=[0.2,0.15,0.9,0.9], xs=1

for i=0,n_elements(t_integration)-1 do begin
	loc=where(tint eq t_integration[i] and raw_data lt 14000)
	if loc[0] ne -1 then begin
		oplot,data[loc], (photons[loc]-bckg_photon_level)*tint[loc],psym=psym[i],col=col[i]
	endif

	if t_integration[i] lt 250 then begin
		phot=[phot, (photons[loc]-bckg_photon_level)*tint[loc]]
		dat=[dat, data[loc]]
	endif
endfor

;phot_sub=phot-bckg_photon_level

int_str=string(t_integration, format='(i4)')
val=strarr(n_elements(int_str))
val[*]='us'
int_str=int_str+val

legend_, int_str, col=col[0:n_elements(int_str)-1], $
	psym=psym[0:n_elements(int_str)-1], $
	/top, /left, charsize=1.0

keep=where(phot gt 0)
err=sqrt(phot[keep])
err[*]=1e23

;oploterror, dat[keep], phot[keep], err, psym=3

fit_phot=mpfitfun('linear', dat[keep], phot[keep], err, $
	[min(phot),2e21])
xv=(findgen(500)/499.)*10e3
yfit=fit_phot[0]+(xv*fit_phot[1])

xyouts, 0.45, 0.85, '#phots = '+string(fit_phot[0], format='(e9.2)')+$
		' + ('+string(fit_phot[1], format='(e9.2)')+')'+'ADC', $;+greek('Delta')+'DL',$
	/normal, charsize=1.0

xyouts, 0.45, 0.75, 'Offset = '+string(bckg_photon_level, format='(e9.2)'), $
	/normal, charsize=1.0
oplot, xv, yfit

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif
;===============================================================

stop

if keyword_set(ps) then begin
	atpsopen, filename=folder+'calib_all_tintscaled.eps'
	setup_ps
endif else window, 20

col=[truecolor(), truecolor('firebrick'), $
	truecolor('royalblue'), truecolor('limegreen'), $
	truecolor('gold'), truecolor('orange'), $
	truecolor('cyan'), truecolor('purple'), $
	truecolor('gray'), truecolor('fuchsia'), $
	truecolor('olive')]

psym=[8,8,8,4,5,7,8,8,8,8,7]

;scale for plot - need to remove saturated values
vals=photons*tint
locate=where(raw_data lt 14000)

max_plot=max(vals[locate], /nan)

phot=[0]
dat=[0]
raw_dat=[0]

plot, [0,16000], [0, max_plot], /nodata, $
	ytitle='!3 Photons (sr!u-1!n m!u-3!n)', $
	xtitle=greek('Delta')+'!3 DL (arb.)', $
	position=[0.15,0.15,0.9,0.9], xs=1

for i=0,n_elements(t_integration)-1 do begin
	loc=where(tint eq t_integration[i] and raw_data lt 14000)
	if loc[0] ne -1 then begin
		oplot,raw_data[loc], (photons[loc])*tint[loc],psym=psym[i],col=col[i]
	endif

	if t_integration[i] lt 250 then begin
		phot=[phot, photons[loc]*tint[loc]]
		dat=[dat, data[loc]]
		raw_dat=[raw_dat, raw_data[loc]]
	endif
endfor

int_str=string(t_integration, format='(i4)')
val=strarr(n_elements(int_str))
val[*]='us'
int_str=int_str+val

legend_, int_str, col=col[0:n_elements(int_str)-1], $
	psym=psym[0:n_elements(int_str)-1], $
	/top, /left, charsize=1.0

keep=where(phot gt 0)
err=sqrt(phot[keep])
err[*]=sqrt(phot[keep[0]])

fit_phot2=mpfitfun('linear', raw_dat[keep], phot[keep], err, $
	[min(phot),2e21])
xv=(findgen(500)/499.)*10e3
yfit=fit_phot2[0]+(xv*fit_phot2[1])

xyouts, 0.4, 0.85, '#phots = '+string(fit_phot2[0], format='(e9.2)')+$
		' + ('+string(fit_phot2[1], format='(e9.2)')+')'+greek('Delta')+'DL',$
	/normal, charsize=1.0

oplot, xv, yfit

if keyword_set(ps) then begin
	atpsclose
	setup_ps, /unset
endif





;take the data at tint=250 ms

loc250=where(temp eq 70 and raw_data lt 14000)

if n_elements(loc250) gt 2 then begin

	if keyword_set(ps) then begin
		atpsopen, filename='tint_vs_counts_60degc.eps'
		setup_ps
	endif else 	window, 12

	plot, tint[loc250], data[loc250], psym=8, $
		position=[0.15,0.15,0.68,0.9], $
		xtitle='!3 Integration time (us)', $
		ytitle='!3 delta(ADC) counts'

	;fit through the ones < 250 us and the ones more than 250us
	tints=tint[loc250]
	datas=data[loc250]
	data_delta=datas
	sel=where(tints lt 150)
	selo=where(tints gt 150)
	fitl250=mpfitfun('linear', tints[sel], datas[sel], sqrt(datas[sel]), $
					[0,3])
	fitg250=mpfitfun('linear', tints[selo], datas[selo], sqrt(datas[selo]), $
					[0,3])

	xv=findgen(1000)
	fitl=fitl250[0]+(xv*fitl250[1])
	fitg=fitg250[0]+(xv*fitg250[1])

	oplot, xv, fitl, col=truecolor('firebrick')
	oplot, xv, fitg, col=truecolor('royalblue')

	legend_, ['!3 points < 150', '!3 points > 150'], $
		psym=[8,8], $
		col=[truecolor('firebrick'), truecolor('royalblue')], $
		/top, /left, charsize=1.0

	if keyword_set(ps) then begin
		atpsclose
		setup_ps, /unset
	endif

	if keyword_set(ps) then begin
		atpsopen, filename='tint_vs_raw_counts_60degc.eps'
		setup_ps
	endif else 	window, 13

	plot, tint[loc250], raw_data[loc250], psym=8, $
		position=[0.15,0.15,0.68,0.9], $
		xtitle='!3 Integration time (us)', $
		ytitle='!3 Raw counts (signal)'

	tints=tint[loc250]
	datas=raw_data[loc250]
	datas_raw=datas

	fitl250=mpfitfun('linear', tints[sel], datas[sel], sqrt(datas[sel]), $
					[0,3])
	fitg250=mpfitfun('linear', tints[selo], datas[selo], sqrt(datas[selo]), $
					[0,3])

	xv=findgen(1000)
	fitl=fitl250[0]+(xv*fitl250[1])
	fitg=fitg250[0]+(xv*fitg250[1])

	oplot, xv, fitl, col=truecolor('firebrick')
	oplot, xv, fitg, col=truecolor('royalblue')

	legend_, ['!3 points < 150', '!3 points > 150'], $
		psym=[8,8], $
		col=[truecolor('firebrick'), truecolor('royalblue')], $
		/top, /left, charsize=1.0

	if keyword_set(ps) then begin
		atpsclose
		setup_ps, /unset
	endif

	if keyword_set(ps) then begin
		atpsopen, filename='tint_vs_bck_counts_60degc.eps'
		setup_ps
	endif else 	window, 15

	plot, tint[loc250], bck_data[loc250], psym=8, $
		position=[0.15,0.15,0.68,0.9], $
		xtitle='!3 Integration time (us)', $
		ytitle='!3 Raw counts (background)'

	tints=tint[loc250]
	datas=bck_data[loc250]

	fitl250=mpfitfun('linear', tints[sel], datas[sel], sqrt(datas[sel]), $
					[0,3])
	fitg250=mpfitfun('linear', tints[selo], datas[selo], sqrt(datas[selo]), $
					[0,3])

	xv=findgen(1000)
	fitl=fitl250[0]+(xv*fitl250[1])
	fitg=fitg250[0]+(xv*fitg250[1])

	oplot, xv, fitl, col=truecolor('firebrick')
	oplot, xv, fitg, col=truecolor('royalblue')

	legend_, ['!3 points < 150', '!3 points > 150'], $
		psym=[8,8], $
		col=[truecolor('firebrick'), truecolor('royalblue')], $
		/top, /left, charsize=1.0

	if keyword_set(ps) then begin
		atpsclose
		setup_ps, /unset
	endif

endif

;calculate counts at 60deg vs tint
window, 16
calc_counts=data_delta[0]*(tints/100)
plot, tints, calc_counts, psym=8                       
oplot, tints, data_delta, psym=8, col=truecolor('red')


stop

END
