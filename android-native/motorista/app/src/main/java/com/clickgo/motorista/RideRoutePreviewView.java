package com.clickgo.motorista;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** Draws a route preview directly on Canvas; no map tiles, API calls or billing. */
public final class RideRoutePreviewView extends View {
    private final Paint route=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint dot=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint bg=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<double[]> pts=new ArrayList<>();

    public RideRoutePreviewView(Context context){
        super(context);
        route.setColor(Color.rgb(30,30,30));route.setStyle(Paint.Style.STROKE);route.setStrokeWidth(dp(4));route.setStrokeCap(Paint.Cap.ROUND);route.setStrokeJoin(Paint.Join.ROUND);
        bg.setColor(Color.rgb(239,239,239));dot.setStyle(Paint.Style.FILL);setMinimumHeight((int)dp(112));
    }

    public void setPoints(JSONArray rows){pts.clear();if(rows!=null)for(int i=0;i<rows.length();i++){JSONObject p=rows.optJSONObject(i);if(p==null)continue;double lat=p.optDouble("lat",Double.NaN),lng=p.optDouble("lng",Double.NaN);if(Double.isFinite(lat)&&Double.isFinite(lng))pts.add(new double[]{lat,lng});}invalidate();}

    @Override protected void onDraw(Canvas c){super.onDraw(c);c.drawRoundRect(0,0,getWidth(),getHeight(),dp(14),dp(14),bg);if(pts.size()<2)return;double minLat=Double.POSITIVE_INFINITY,maxLat=Double.NEGATIVE_INFINITY,minLng=Double.POSITIVE_INFINITY,maxLng=Double.NEGATIVE_INFINITY;for(double[] p:pts){minLat=Math.min(minLat,p[0]);maxLat=Math.max(maxLat,p[0]);minLng=Math.min(minLng,p[1]);maxLng=Math.max(maxLng,p[1]);}double latSpan=Math.max(0.00001,maxLat-minLat),lngSpan=Math.max(0.00001,maxLng-minLng);float pad=dp(16),w=Math.max(1,getWidth()-2*pad),h=Math.max(1,getHeight()-2*pad);Path path=new Path();for(int i=0;i<pts.size();i++){double[] p=pts.get(i);float x=pad+(float)((p[1]-minLng)/lngSpan)*w;float y=pad+(1f-(float)((p[0]-minLat)/latSpan))*h;if(i==0)path.moveTo(x,y);else path.lineTo(x,y);}c.drawPath(path,route);double[] a=pts.get(0),b=pts.get(pts.size()-1);float ax=pad+(float)((a[1]-minLng)/lngSpan)*w,ay=pad+(1f-(float)((a[0]-minLat)/latSpan))*h,bx=pad+(float)((b[1]-minLng)/lngSpan)*w,by=pad+(1f-(float)((b[0]-minLat)/latSpan))*h;dot.setColor(Color.rgb(255,212,0));c.drawCircle(ax,ay,dp(7),dot);dot.setColor(Color.rgb(230,70,65));c.drawCircle(bx,by,dp(7),dot);}

    private float dp(float v){return v*getResources().getDisplayMetrics().density;}
}
