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

# CLICK-GO Motorista v3.11 PRIME
# Mapa de calor de demanda + raio configurado pelo franqueado + zonas dinamicas visiveis.

# Repository: mercado agregado do motorista, sem dados pessoais de passageiros.
repo_anchor='''    public static JSONObject firstOffer(String token) throws Exception {\n        JSONArray rows = new JSONArray(ApiClient.rpc("get_driver_pending_offers", new JSONObject(), token));\n        return rows.length() > 0 ? rows.getJSONObject(0) : null;\n    }\n'''
repo_add=repo_anchor+'''\n    public static JSONObject marketMap(String token) throws Exception {\n        return new JSONObject(ApiClient.rpc("get_driver_market_map", new JSONObject(), token));\n    }\n'''
if 'public static JSONObject marketMap(' not in repo:
    if repo_anchor not in repo:
        raise SystemExit('firstOffer nao encontrado no DriverRepository')
    repo=repo.replace(repo_anchor,repo_add,1)

# Renderer: overlay customizado para manter calor/zonas legiveis mesmo quando o mapa e redesenhado.
if 'class MarketOverlay extends org.osmdroid.views.overlay.Overlay' not in renderer:
    renderer=renderer.replace('import android.graphics.Color;\n', '''import android.graphics.Color;\nimport android.graphics.Canvas;\nimport android.graphics.Paint;\nimport android.graphics.Point;\nimport android.graphics.RectF;\n''',1)
    renderer=renderer.replace('import org.json.JSONObject;\n', 'import org.json.JSONObject;\nimport org.json.JSONArray;\n',1)
    insert='''\n    public static void renderMarketLayers(MapView map, Location current, JSONObject market, int strokeWidth) {\n        if (map == null || market == null || market.length() == 0) return;\n        // Remove apenas overlays de mercado anteriores; preserva rota, motorista e marcadores da corrida.\n        for (int i = map.getOverlays().size() - 1; i >= 0; i--) {\n            if (map.getOverlays().get(i) instanceof MarketOverlay) map.getOverlays().remove(i);\n        }\n        map.getOverlays().add(new MarketOverlay(current, market, Math.max(2, strokeWidth)));\n        map.invalidate();\n    }\n\n    private static final class MarketOverlay extends org.osmdroid.views.overlay.Overlay {\n        private final Location current;\n        private final JSONObject market;\n        private final int strokeWidth;\n        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Paint textBg = new Paint(Paint.ANTI_ALIAS_FLAG);\n        private final Point centerPx = new Point();\n        private final Point edgePx = new Point();\n        private final Point pointPx = new Point();\n\n        MarketOverlay(Location current, JSONObject market, int strokeWidth) {\n            this.current=current;this.market=market;this.strokeWidth=strokeWidth;\n            textPaint.setColor(Color.rgb(17,17,17));textPaint.setTextSize(30f);textPaint.setFakeBoldText(true);textPaint.setTextAlign(Paint.Align.CENTER);\n            textBg.setColor(Color.rgb(255,212,0));textBg.setStyle(Paint.Style.FILL);\n        }\n\n        @Override public void draw(Canvas canvas, MapView mapView, boolean shadow) {\n            if (shadow || canvas == null || mapView == null) return;\n            final org.osmdroid.views.Projection projection=mapView.getProjection();\n            JSONArray heat=market.optJSONArray("heatmap");\n            if(heat!=null){\n                for(int i=0;i<heat.length();i++){\n                    JSONObject h=heat.optJSONObject(i);if(h==null)continue;double lat=h.optDouble("lat",Double.NaN),lng=h.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))continue;\n                    int score=Math.max(0,Math.min(100,h.optInt("score",0)));projection.toPixels(new GeoPoint(lat,lng),pointPx);\n                    float radius=18f+(score*0.32f);paint.setStyle(Paint.Style.FILL);paint.setColor(Color.argb(45+Math.min(105,score),255,88,35));canvas.drawCircle(pointPx.x,pointPx.y,radius,paint);\n                    paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2f);paint.setColor(Color.argb(150,220,65,20));canvas.drawCircle(pointPx.x,pointPx.y,radius,paint);\n                }\n            }\n            JSONArray zones=market.optJSONArray("dynamic_zones");\n            if(zones!=null){\n                for(int i=0;i<zones.length();i++){\n                    JSONObject z=zones.optJSONObject(i);if(z==null)continue;double lat=z.optDouble("lat",Double.NaN),lng=z.optDouble("lng",Double.NaN),radiusKm=z.optDouble("radius_km",0);if(!Double.isFinite(lat)||!Double.isFinite(lng)||radiusKm<=0)continue;\n                    boolean active=z.optBoolean("active_now",false);float radiusPx=geoRadiusPx(projection,lat,lng,radiusKm);projection.toPixels(new GeoPoint(lat,lng),centerPx);\n                    paint.setStyle(Paint.Style.FILL);paint.setColor(active?Color.argb(38,255,212,0):Color.argb(18,120,120,120));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);\n                    paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(strokeWidth+2f);paint.setColor(active?Color.rgb(255,180,0):Color.rgb(125,125,125));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);\n                    String label=String.format(java.util.Locale.getDefault(),"%.2fx",z.optDouble("multiplier",1));float w=textPaint.measureText(label)+26f;float h=46f;textBg.setColor(active?Color.rgb(255,212,0):Color.rgb(210,210,210));canvas.drawRoundRect(new RectF(centerPx.x-w/2f,centerPx.y-h/2f,centerPx.x+w/2f,centerPx.y+h/2f),14f,14f,textBg);canvas.drawText(label,centerPx.x,centerPx.y+10f,textPaint);\n                }\n            }\n            double pickup=market.optDouble("pickup_radius_km",0);\n            if(current!=null&&pickup>0){double lat=current.getLatitude(),lng=current.getLongitude();float radiusPx=geoRadiusPx(projection,lat,lng,pickup);projection.toPixels(new GeoPoint(lat,lng),centerPx);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(Math.max(2f,strokeWidth));paint.setColor(Color.argb(150,35,130,235));canvas.drawCircle(centerPx.x,centerPx.y,radiusPx,paint);}\n        }\n\n        private float geoRadiusPx(org.osmdroid.views.Projection projection,double lat,double lng,double radiusKm){\n            projection.toPixels(new GeoPoint(lat,lng),centerPx);double edgeLat=Math.max(-89.9,Math.min(89.9,lat+(radiusKm/111.32)));projection.toPixels(new GeoPoint(edgeLat,lng),edgePx);return Math.max(8f,(float)Math.hypot(edgePx.x-centerPx.x,edgePx.y-centerPx.y));\n        }\n    }\n'''
    pos=renderer.rfind('\n}')
    if pos<0: raise SystemExit('fim do DriverMapRenderer nao encontrado')
    renderer=renderer[:pos]+insert+renderer[pos:]

# MainActivity: cache e legenda do mercado.
field_anchor='    private MapView map;\n'
if 'private JSONObject driverMarketData' not in text:
    if field_anchor not in text: raise SystemExit('campo map nao encontrado')
    text=text.replace(field_anchor,field_anchor+'''    private JSONObject driverMarketData = new JSONObject();\n    private long driverMarketUpdatedAtMs = 0L;\n    private TextView driverMarketHint;\n''',1)

# Insere uma legenda logo abaixo do mapa final gerado pela cadeia PRIME.
map_home_pat=re.compile(r'(FrameLayout frame = new FrameLayout\(this\);.*?root\.addView\(frame,new LinearLayout\.LayoutParams\(-1,dp\(340\)\)\);\s*root\.addView\(space\(12\)\);)',re.S)
if 'Mapa de calor' not in text:
    m=map_home_pat.search(text)
    if not m: raise SystemExit('mapa da home nao encontrado para legenda')
    block=m.group(1)+'''\n        driverMarketHint=text("Mapa de calor · dinâmica · raio de chamadas",12,Color.rgb(205,205,205),true);\n        driverMarketHint.setPadding(dp(4),0,dp(4),dp(8));root.addView(driverMarketHint);\n'''
    text=text[:m.start()]+block+text[m.end():]

# Helpers antes de toggleOnline, que continua existindo na versao final.
helper_anchor='    private void toggleOnline() {'
helpers=r'''    private void refreshDriverMarketMap(boolean force){
        if(token==null||token.isBlank()||destroyed||!"approved".equalsIgnoreCase(driverStatus))return;
        long now=System.currentTimeMillis();
        if(!force&&now-driverMarketUpdatedAtMs<30000L){DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));return;}
        driverMarketUpdatedAtMs=now;
        io.execute(()->{try{
            JSONObject market=DriverRepository.marketMap(token);
            ui.post(()->{if(destroyed||isFinishing())return;driverMarketData=market==null?new JSONObject():market;DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));if(driverMarketHint!=null){int hot=driverMarketData.optJSONArray("heatmap")==null?0:driverMarketData.optJSONArray("heatmap").length();int zones=driverMarketData.optJSONArray("dynamic_zones")==null?0:driverMarketData.optJSONArray("dynamic_zones").length();driverMarketHint.setText("🔥 "+hot+" ponto(s) de demanda · ⚡ "+zones+" dinâmica(s) · raio "+String.format(Locale.getDefault(),"%.1f km",driverMarketData.optDouble("pickup_radius_km",0)));}});
        }catch(Exception e){ui.post(()->{if(driverMarketHint!=null)driverMarketHint.setText("Mapa de demanda temporariamente indisponível");});}});
    }

'''
if 'private void refreshDriverMarketMap(' not in text:
    if helper_anchor not in text: raise SystemExit('toggleOnline nao encontrado para helper do mapa')
    text=text.replace(helper_anchor,helpers+helper_anchor,1)

# Carrega assim que a Home terminou de renderizar. Funciona tanto na baseline quanto na Home PRIME reescrita.
if 'refreshDriverMarketMap(true);' not in text:
    set_content_matches=list(re.finditer(r'setContentView\((?:scroll\(root,BLACK\)|root)\);',text))
    # Preferimos a ultima ocorrencia antes de toggleOnline: e a Home final.
    candidates=[m for m in set_content_matches if m.start()<text.find(helper_anchor)]
    if not candidates: raise SystemExit('setContentView da home nao encontrado')
    m=candidates[-1]
    text=text[:m.end()]+'\n        refreshDriverMarketMap(true);'+text[m.end():]

# A cada ciclo de polling, atualiza no maximo a cada 30s.
if 'refreshOperation();refreshDriverMarketMap(false);' not in text:
    text=text.replace('refreshOperation();ui.postDelayed(this,4500);','refreshOperation();refreshDriverMarketMap(false);ui.postDelayed(this,4500);',1)

# Depois de toda renderizacao de mapa existente, repoe as camadas de mercado, pois render() limpa overlays.
lines=text.splitlines()
out=[]
for line in lines:
    out.append(line)
    if 'DriverMapRenderer.render(map,' in line and 'renderMarketLayers' not in line:
        indent=line[:len(line)-len(line.lstrip())]
        out.append(indent+'DriverMapRenderer.renderMarketLayers(map,currentLocation,driverMarketData,dp(3));')
text='\n'.join(out)+'\n'

for required in ['get_driver_market_map','refreshDriverMarketMap(true)','renderMarketLayers(map,currentLocation,driverMarketData','Mapa de calor','pickup_radius_km']:
    if required not in text and required not in repo and required not in renderer: raise SystemExit('Mapa motorista incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 311',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.11-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
repo_path.write_text(repo,encoding='utf-8')
map_path.write_text(renderer,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.11 PRIME: mapa de calor, raio de chamada e dinamicas visiveis no mapa.')
