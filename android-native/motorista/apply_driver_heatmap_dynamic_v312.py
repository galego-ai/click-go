from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
map_path=Path('app/src/main/java/com/clickgo/motorista/DriverMapRenderer.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
renderer=map_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v3.12 PRIME
# Mapa de calor agregado + raio efetivo de chamadas + zonas dinamicas/valores no mapa.

# 1) Endpoint de mercado do motorista.
repo_anchor='''    public static JSONObject firstOffer(String token) throws Exception {\n        JSONArray rows = new JSONArray(ApiClient.rpc("get_driver_pending_offers", new JSONObject(), token));\n        return rows.length() > 0 ? rows.getJSONObject(0) : null;\n    }\n'''
if 'public static JSONObject marketMap(' not in repo:
    if repo_anchor not in repo:
        raise SystemExit('firstOffer nao encontrado no DriverRepository')
    repo=repo.replace(repo_anchor,repo_anchor+'''\n    public static JSONObject marketMap(String token) throws Exception {\n        return new JSONObject(ApiClient.rpc("get_driver_market_map", new JSONObject(), token));\n    }\n''',1)

# 2) O renderizador guarda a ultima camada de mercado e a recoloca automaticamente
# sempre que uma corrida/oferta redesenha o mapa e limpa os overlays.
if 'private static JSONObject lastMarketData' not in renderer:
    renderer=renderer.replace('import android.graphics.Color;\n', '''import android.graphics.Color;\nimport android.graphics.Canvas;\nimport android.graphics.Paint;\nimport android.graphics.Point;\nimport android.graphics.RectF;\n''',1)
    renderer=renderer.replace('import org.json.JSONObject;\n', 'import org.json.JSONObject;\nimport org.json.JSONArray;\n',1)
    class_anchor='''public final class DriverMapRenderer {\n    private DriverMapRenderer() {}\n'''
    state='''public final class DriverMapRenderer {\n    private static JSONObject lastMarketData = new JSONObject();\n    private static Location lastMarketLocation;\n    private static int lastMarketStrokeWidth = 3;\n    private DriverMapRenderer() {}\n'''
    if class_anchor not in renderer:
        raise SystemExit('classe DriverMapRenderer nao encontrada')
    renderer=renderer.replace(class_anchor,state,1)

    # Depois que o mapa comum foi reconstruido, a camada de mercado volta por cima.
    end_render='''        map.invalidate();\n    }\n\n    private static void marker'''
    end_repl='''        appendMarketOverlay(map, current);\n        map.invalidate();\n    }\n\n    public static void renderMarketLayers(MapView map, Location current, JSONObject market, int strokeWidth) {\n        if (market != null) lastMarketData = market;\n        if (current != null) lastMarketLocation = current;\n        lastMarketStrokeWidth = Math.max(2, strokeWidth);\n        if (map == null) return;\n        for (int i=map.getOverlays().size()-1;i>=0;i--) {\n            if (map.getOverlays().get(i) instanceof MarketOverlay) map.getOverlays().remove(i);\n        }\n        appendMarketOverlay(map,current);\n        map.invalidate();\n    }\n\n    private static void appendMarketOverlay(MapView map, Location current) {\n        if (map == null || lastMarketData == null || lastMarketData.length() == 0) return;\n        Location loc=current!=null?current:lastMarketLocation;\n        map.getOverlays().add(new MarketOverlay(loc,lastMarketData,lastMarketStrokeWidth));\n    }\n\n    private static final class MarketOverlay extends org.osmdroid.views.overlay.Overlay {\n        private final Location current;\n        private final JSONObject market;\n        private final int strokeWidth;\n        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Paint textPaint=new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Paint textBg=new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Point centerPx=new Point();\n        private final Point edgePx=new Point();\n        private final Point pointPx=new Point();\n\n        MarketOverlay(Location current,JSONObject market,int strokeWidth){\n            this.current=current;this.market=market;this.strokeWidth=strokeWidth;\n            textPaint.setColor(Color.rgb(17,17,17));textPaint.setTextSize(30f);textPaint.setFakeBoldText(true);textPaint.setTextAlign(Paint.Align.CENTER);\n            textBg.setStyle(Paint.Style.FILL);\n        }\n\n        @Override public void draw(Canvas canvas,MapView mapView,boolean shadow){\n            if(shadow||canvas==null||mapView==null)return;\n            org.osmdroid.views.Projection projection=mapView.getProjection();\n\n            // Heatmap: somente pontos agregados de demanda, nunca passageiro/endereco individual.\n            JSONArray heat=market.optJSONArray("heatmap");\n            if(heat!=null){\n                for(int i=0;i<heat.length();i++){\n                    JSONObject h=heat.optJSONObject(i);if(h==null)continue;\n                    double lat=h.optDouble("lat",Double.NaN),lng=h.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))continue;\n                    int score=Math.max(0,Math.min(100,h.optInt("score",0)));\n                    projection.toPixels(new GeoPoint(lat,lng),pointPx);\n                    float radius=18f+(score*0.32f);\n                    paint.setStyle(Paint.Style.FILL);paint.setColor(Color.argb(45+Math.min(105,score),255,88,35));canvas.drawCircle(pointPx.x,pointPx.y,radius,paint);\n                    paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2f);paint.setColor(Color.argb(150,220,65,20));canvas.drawCircle(pointPx.x,pointPx.y,radius,paint);\n                }\n            }\n\n            // Dinamicas cadastradas pelo franqueado: circulo e multiplicador no proprio mapa.\n            JSONArray zones=market.optJSONArray("dynamic_zones");\n            if(zones!=null){\n                for(int i=0;i<zones.length();i++){\n                    JSONObject z=zones.optJSONObject(i);if(z==null)continue;\n                    double lat=z.optDouble("lat",Double.NaN),lng=z.optDouble("lng",Double.NaN),radiusKm=z.optDouble("radius_km",0);\n                    if(!Double.isFinite(lat)||!Double.isFinite(lng)||radiusKm<=0)continue;\n                    boolean active=z.optBoolean("active_now",false);\n                    float radiusPx=geoRadiusPx(projection,lat,lng,radiusKm);projection.toPixels(new GeoPoint(lat,lng),centerPx);\n                    paint.setStyle(Paint.Style.FILL);paint.setColor(active?Color.argb(42,255,212,0):Color.argb(15,120,120,120));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);\n                    paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(strokeWidth+2f);paint.setColor(active?Color.rgb(255,180,0):Color.rgb(125,125,125));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);\n                    String label=String.format(java.util.Locale.getDefault(),"%.2fx",z.optDouble("multiplier",1));\n                    float w=textPaint.measureText(label)+26f,h=46f;textBg.setColor(active?Color.rgb(255,212,0):Color.rgb(210,210,210));\n                    canvas.drawRoundRect(new RectF(centerPx.x-w/2f,centerPx.y-h/2f,centerPx.x+w/2f,centerPx.y+h/2f),14f,14f,textBg);\n                    canvas.drawText(label,centerPx.x,centerPx.y+10f,textPaint);\n                }\n            }\n\n            // Raio efetivo configurado pela franquia/cidade.\n            double pickup=market.optDouble("pickup_radius_km",0);\n            if(current!=null&&pickup>0){\n                double lat=current.getLatitude(),lng=current.getLongitude();float radiusPx=geoRadiusPx(projection,lat,lng,pickup);projection.toPixels(new GeoPoint(lat,lng),centerPx);\n                paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(Math.max(2f,strokeWidth));paint.setColor(Color.argb(155,35,130,235));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);\n            }\n        }\n\n        private float geoRadiusPx(org.osmdroid.views.Projection projection,double lat,double lng,double radiusKm){\n            projection.toPixels(new GeoPoint(lat,lng),centerPx);\n            double edgeLat=Math.max(-89.9,Math.min(89.9,lat+(radiusKm/111.32)));projection.toPixels(new GeoPoint(edgeLat,lng),edgePx);\n            return Math.max(8f,(float)Math.hypot(edgePx.x-centerPx.x,edgePx.y-centerPx.y));\n        }\n    }\n\n    private static void marker'''
    if end_render not in renderer:
        raise SystemExit('fim do render do mapa nao encontrado')
    renderer=renderer.replace(end_render,end_repl,1)

# 3) Cache de mercado no app.
field_anchor='    private MapView map;\n'
if 'private JSONObject driverMarketData' not in text:
    if field_anchor not in text: raise SystemExit('campo map nao encontrado')
    text=text.replace(field_anchor,field_anchor+'''    private JSONObject driverMarketData = new JSONObject();\n    private long driverMarketUpdatedAtMs = 0L;\n''',1)

helper_anchor='    private void toggleOnline() {'
helpers=r'''    private void refreshDriverMarketMap(boolean force){
        if(token==null||token.isBlank()||destroyed||!"approved".equalsIgnoreCase(driverStatus))return;
        long now=System.currentTimeMillis();
        if(!force&&now-driverMarketUpdatedAtMs<30000L){DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));return;}
        driverMarketUpdatedAtMs=now;
        io.execute(()->{try{
            JSONObject market=DriverRepository.marketMap(token);
            ui.post(()->{if(destroyed||isFinishing())return;driverMarketData=market==null?new JSONObject():market;DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));});
        }catch(Exception ignored){} });
    }

'''
if 'private void refreshDriverMarketMap(' not in text:
    if helper_anchor not in text: raise SystemExit('toggleOnline nao encontrado')
    text=text.replace(helper_anchor,helpers+helper_anchor,1)

# A Home final sempre chama loadHomeTaximeter; usamos isso como ancora estavel da cadeia PRIME.
if 'refreshDriverMarketMap(true);' not in text:
    home_load='        loadHomeTaximeter(homeTaximeter);\n'
    if home_load not in text: raise SystemExit('loadHomeTaximeter(homeTaximeter) nao encontrado na Home final')
    text=text.replace(home_load,home_load+'        refreshDriverMarketMap(true);\n',1)

# Toda atualizacao operacional tambem tenta renovar demanda/dinamica (throttle interno de 30s).
if 'refreshDriverMarketMap(false);' not in text:
    m=re.search(r'(    private void refreshOperation\(\)\s*\{)',text)
    if not m: raise SystemExit('refreshOperation nao encontrado')
    text=text[:m.end()]+' refreshDriverMarketMap(false);'+text[m.end():]

# A posicao muda mais rapido que os dados; reaplica o raio em volta da localizacao atual sem nova chamada de rede.
if 'DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));' not in text[text.find('locationListener'):]:
    listener='locationListener = loc -> { currentLocation=loc;'
    if listener in text:
        text=text.replace(listener,listener+' DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));',1)

for required in ['get_driver_market_map','refreshDriverMarketMap(true)','refreshDriverMarketMap(false)','renderMarketLayers','MarketOverlay','pickup_radius_km','dynamic_zones','heatmap']:
    if required not in text and required not in repo and required not in renderer:
        raise SystemExit('Mapa motorista incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 312',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.12-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
repo_path.write_text(repo,encoding='utf-8')
map_path.write_text(renderer,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.12 PRIME: mapa de calor, raio de chamadas e valores dinamicos no mapa.')
