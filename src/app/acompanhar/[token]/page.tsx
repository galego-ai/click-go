import PublicRideShareTracker from '@/components/PublicRideShareTracker'
export default async function Page({params}:{params:Promise<{token:string}>}){const{token}=await params;return <PublicRideShareTracker token={token}/>}
