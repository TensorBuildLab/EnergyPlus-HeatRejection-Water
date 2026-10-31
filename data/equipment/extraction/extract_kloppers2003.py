import re,sys
L=open(sys.argv[1]).read().split('\n')
def rows(a,b):
    out=[]
    for l in L[a-1:b]:
        l=l.replace('43.444j, ;','43.444').replace('42.934 ;','42.934').replace('.21.264','21.264').replace('l.771','1.771').replace('2,949','2.949').replace('. 1.482','1.482').replace('4l.l 86','41.186');l=re.sub(r'^I ','1 ',l).replace('44:044','44.044').replace('17,.227','17.227')
        l=l.replace('\\.','1.').replace('..','.').replace(',','.').replace('"','').replace("'",'').replace('5\\.','51.')
        t=re.findall(r'-?\d+\.\d+|\b\d+\b',l)
        if len(t)>=8 and t[0].isdigit(): out.append(t)
    return out
cases=[('trickle',1.08,13502,13520,13522,13543,100060),('trickle',1.53,13636,13654,13656,13684,101340),('trickle',1.98,13784,13809,13811,13832,100970),
('splash_0.1m',2.5,15327,15346,15348,15370,100490),('film',0.6,15976,15995,15997,16019,100620),('film',0.9,16111,16128,16133,16150,100950),('film',1.2,16247,16266,16268,16291,101020)]
print('fill,Lfi_m,p_Pa,test,Tdb_in_C,Twb_in_C,Tw_in_C,Tw_out_C,ma_kg_s,mw_kg_s,dp_Pa,Ta_out_meas_C,Gw,Ga,L_over_G,Me_Merkel,Me_eNTU,Me_Poppe,Ta_out_Poppe_C,Ta_out_Merkel_C')
for f,Lfi,a,b,c,d,p in cases:
    m=rows(a,b); r=rows(c,d)
    if len(m)!=18 or len(r)!=18: print('#WARN',f,Lfi,len(m),len(r),file=sys.stderr)
    for x,y in zip(m,r):
        Gw,Ga,mM,mE,mP=map(float,y[1:6])
        print(f"{f},{Lfi},{p},{x[0]},"+",".join(x[1:9])+f",{Gw},{Ga},{Gw/Ga:.3f},{mM*Lfi:.3f},{mE*Lfi:.3f},{mP*Lfi:.3f},{y[8]},{y[9]}")
