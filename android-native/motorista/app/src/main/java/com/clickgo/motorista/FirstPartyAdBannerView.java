package com.clickgo.motorista;

import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** First-party CLICK-GO banner slot; no advertising SDK or per-impression billing. */
public final class FirstPartyAdBannerView extends FrameLayout {
    private static final int MAX_IMAGE_BYTES=2*1024*1024;
    private final ExecutorService imageIo=Executors.newSingleThreadExecutor();
    private final ImageView image;
    private final TextView title;
    private final TextView sponsor;
    private String targetUrl="";
    private volatile int loadSeq;

    public FirstPartyAdBannerView(Context context){
        super(context);setVisibility(GONE);setClickable(true);setFocusable(true);setClipToOutline(true);setBackground(round(Color.WHITE,16,Color.rgb(225,225,225)));
        image=new ImageView(context);image.setScaleType(ImageView.ScaleType.CENTER_CROP);image.setBackgroundColor(Color.rgb(245,245,245));addView(image,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout caption=new LinearLayout(context);caption.setOrientation(LinearLayout.VERTICAL);caption.setPadding(dp(12),dp(6),dp(12),dp(7));caption.setBackgroundColor(Color.argb(205,255,255,255));
        title=new TextView(context);title.setTextSize(13);title.setTextColor(Color.rgb(25,25,25));title.setTypeface(Typeface.DEFAULT,Typeface.BOLD);title.setMaxLines(1);
        sponsor=new TextView(context);sponsor.setTextSize(10);sponsor.setTextColor(Color.rgb(90,90,90));sponsor.setMaxLines(1);
        caption.addView(title,new LinearLayout.LayoutParams(-1,dp(21)));caption.addView(sponsor,new LinearLayout.LayoutParams(-1,dp(17)));FrameLayout.LayoutParams cp=new FrameLayout.LayoutParams(-1,dp(46));cp.gravity=Gravity.BOTTOM;addView(caption,cp);
        setOnClickListener(v->openTarget());
    }

    public void setBanner(JSONObject banner){
        final int seq=++loadSeq;if(banner==null){setVisibility(GONE);targetUrl="";image.setImageDrawable(null);return;}
        String label=banner.optString("title","Oferta CLICK-GO").trim(),advertiser=banner.optString("advertiser_name","").trim(),imageUrl=banner.optString("image_url","").trim();targetUrl=banner.optString("target_url","").trim();
        title.setText(label.isBlank()?"Oferta CLICK-GO":label);sponsor.setText(advertiser.isBlank()?"Patrocinado":"Patrocinado · "+advertiser);setContentDescription("Anúncio: "+title.getText());setVisibility(VISIBLE);image.setImageDrawable(null);
        if(!imageUrl.startsWith("https://"))return;
        imageIo.execute(()->{Bitmap bitmap=downloadSmallBitmap(imageUrl);post(()->{if(seq==loadSeq&&bitmap!=null&&isAttachedToWindow())image.setImageBitmap(bitmap);});});
    }

    private Bitmap downloadSmallBitmap(String value){
        HttpURLConnection connection=null;try{connection=(HttpURLConnection)new URL(value).openConnection();connection.setConnectTimeout(4500);connection.setReadTimeout(6000);connection.setInstanceFollowRedirects(true);connection.setUseCaches(true);int code=connection.getResponseCode();if(code<200||code>=300)return null;int declared=connection.getContentLength();if(declared>MAX_IMAGE_BYTES)return null;try(InputStream in=connection.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream(Math.max(8192,Math.min(Math.max(declared,0),MAX_IMAGE_BYTES)))){byte[] buf=new byte[8192];int n,total=0;while((n=in.read(buf))>0){total+=n;if(total>MAX_IMAGE_BYTES)return null;out.write(buf,0,n);}byte[] data=out.toByteArray();return BitmapFactory.decodeByteArray(data,0,data.length);}}catch(Exception ignored){return null;}finally{if(connection!=null)connection.disconnect();}
    }

    private void openTarget(){String u=targetUrl;if(u==null||!u.startsWith("https://"))return;try{getContext().startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(u)));}catch(Exception ignored){}}
    @Override protected void onDetachedFromWindow(){super.onDetachedFromWindow();++loadSeq;try{imageIo.shutdownNow();}catch(Exception ignored){}}
    private GradientDrawable round(int fill,int radius,int stroke){GradientDrawable d=new GradientDrawable();d.setColor(fill);d.setCornerRadius(dp(radius));d.setStroke(dp(1),stroke);return d;}
    private int dp(int v){return (int)(v*getResources().getDisplayMetrics().density+.5f);}
}
