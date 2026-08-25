from pathlib import Path
p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
t=p.read_text()
old='''double baseFare=ride.isNull("final_fare")?ride.optDouble("estimated_fare",0):ride.optDouble("final_fare",0),recordedWait=ride.optDouble("wait_charge_amount",0);\n                JSONObject driverLocation=null,driverCard=null,waitSnapshot=null;'''
new='''double baseFare=ride.isNull("final_fare")?ride.optDouble("estimated_fare",0):ride.optDouble("final_fare",0),recordedWait=ride.optDouble("wait_charge_amount",0);\n                boolean transitionNow=(status.equals("accepted")||status.equals("driver_arriving")||status.equals("in_progress"))&&!driverId.isBlank()&&!trackingUiActive;\n                if(transitionNow){\n                    ui.post(()->{\n                        if(destroyed||isFinishing()||activeRideId==null||!rideId.equals(activeRideId)||trackingUiActive)return;\n                        activeRideStatus=status;trackingUiActive=true;renderedDriverId=null;\n                        getPreferences(MODE_PRIVATE).edit().putString("active_ride_id",rideId).apply();\n                        showActiveRide();\n                    });\n                    return;\n                }\n                JSONObject driverLocation=null,driverCard=null,waitSnapshot=null;'''
if old not in t: raise SystemExit('transition marker not found')
t=t.replace(old,new,1)
p.write_text(t)
print('Passageiro v2.19 transition: aceite abre acompanhamento antes de consultas secundarias.')
