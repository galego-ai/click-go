export type GeoPoint = {
  lat: number
  lng: number
}

const EARTH_RADIUS_METERS = 6_371_000
const toRadians = (degrees: number) => (degrees * Math.PI) / 180

export function distanceMeters(a: GeoPoint, b: GeoPoint): number {
  const lat1 = toRadians(a.lat)
  const lat2 = toRadians(b.lat)
  const deltaLat = toRadians(b.lat - a.lat)
  const deltaLng = toRadians(b.lng - a.lng)

  const h =
    Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) ** 2

  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.min(1, Math.sqrt(h)))
}
