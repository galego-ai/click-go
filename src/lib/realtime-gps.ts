export type DriverLocationBroadcast = {
  driver_id: string
  lat: number
  lng: number
  heading: number | null
  speed_kmh: number | null
  updated_at: string
}

export const cityDriverLocationsTopic = (cityId: string) =>
  `city:${cityId}:driver-locations`

export const rideDriverLocationTopic = (rideId: string) =>
  `ride:${rideId}:driver-location`

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function nullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function parseDriverLocationBroadcast(
  value: unknown,
): DriverLocationBroadcast | null {
  if (!isRecord(value)) return null

  const driverId = value.driver_id
  const lat = value.lat
  const lng = value.lng
  const updatedAt = value.updated_at

  if (
    typeof driverId !== 'string' ||
    typeof lat !== 'number' ||
    !Number.isFinite(lat) ||
    typeof lng !== 'number' ||
    !Number.isFinite(lng) ||
    typeof updatedAt !== 'string'
  ) {
    return null
  }

  return {
    driver_id: driverId,
    lat,
    lng,
    heading: nullableNumber(value.heading),
    speed_kmh: nullableNumber(value.speed_kmh),
    updated_at: updatedAt,
  }
}
