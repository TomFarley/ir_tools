FUNCTION raw_to_temp_tint, ps=ps, folder, integration, temp, lam_range, region, debug=debug

;version of raw_to_temp that uses the calibration found from using photons
;rather than photon flux

;program to use the calibration to convert image to temperature
folders=['IRcam_0101_50mm_20181121', $
		'IRcam_0102_50mm_20181126', $
		'IRcam_0102_50mm_no_ND_20181129',$
		'IRcam_0101_50mm_no_ND_20190219',$
		'FLIR_45_25mm_20190103', $
		'FLIR_47_25mm_20181210']

calibration=[[2.13e21, 6.29e20], $
			[1.89e21, 4.78e20], $
			[1.78e21, 1.18e20], $
			[1.80e21, 1.59e20], $
			[9.2e19, 2.87e19], $
			[9.85e19, 5.85e19]]

;find the folder for the calibration
sel=where(folders eq folder)
fold=folders[sel[0]]
calib=calibration[*,sel[0]]

;get the background and blackbody image
path=fold+'/'+temp+'/'
if strmid(fold, 0,1) eq 'I' then begin
	bb_file='bb_'+integration+'us.ASC'
	bg_file='bg_'+integration+'us.ASC'
	dat_st=0
endif
if strmid(fold, 0, 1) eq 'F' then begin
	bb_file='bb_'+integration+'us.asc'
	bg_file='bg_'+integration+'us.asc'
	dat_st=29
endif

if file_test(path+bb_file) eq 1 and file_test(path+bg_file) eq 1 then begin
;read the data in
tmp=read_ascii(path+bb_file, data_start=dat_st)
bb=tmp.field001
tmp=read_ascii(path+bg_file, data_start=dat_st)
bg=tmp.field001

img=(bb-bg)>0

;calculate the calibration coefficients
photon_img=calib[0]+(img*calib[1])/integration

;now look up the photons into a temperature
;make the look up table
temps=findgen(1000)
temperatures=temps
photons=blackbody_phot_arr(temps, lam_range)

;now loop through the rows of the image and interpolate the phots to 
;temperatures
sz=size(img)
tpro=img*0.0

for i=0, sz[2]-1 do begin
	tpro[*,i]=interpol(temperatures, photons, photon_img[*,i])
endfor

avg=mean(tpro[region[0]:region[1], region[2]:region[3]])
bb_avg=mean(bb[region[0]:region[1], region[2]:region[3]])
bg_avg=mean(bg[region[0]:region[1], region[2]:region[3]])
img_avg=mean(img[region[0]:region[1], region[2]:region[3]])

sat_check=max(bb[region[0]:region[1], region[2]:region[3]])
if sat_check gt 14000 then avg=-100

endif else begin
	avg=!values.f_nan
	tpro=0.
	bb=0.
	img=0.0
	bg=0.0
	bg_avg=0.
	bb_avg=0.
	img_avg=0.
endelse

if keyword_set(debug) then stop

data={avg:avg, tpro:tpro, bb:bb, bg:bg, $
		img:img, bb_avg:bb_avg, bg_avg:bg_avg, $
		img_avg:img_avg}

return, data


END
