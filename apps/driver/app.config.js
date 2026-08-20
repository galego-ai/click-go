const base = require('./app.json').expo

module.exports = () => {
  const androidKey = process.env.GOOGLE_MAPS_DRIVER_ANDROID_API_KEY || ''
  const iosKey = process.env.GOOGLE_MAPS_DRIVER_IOS_API_KEY || ''
  const plugins = [...(base.plugins || [])]

  if (androidKey || iosKey) {
    plugins.push([
      'react-native-maps',
      {
        ...(androidKey ? { androidGoogleMapsApiKey: androidKey } : {}),
        ...(iosKey ? { iosGoogleMapsApiKey: iosKey } : {}),
      },
    ])
  }

  return {
    ...base,
    plugins,
    android: {
      ...base.android,
      ...(androidKey
        ? { config: { ...(base.android?.config || {}), googleMaps: { apiKey: androidKey } } }
        : {}),
    },
    ios: {
      ...base.ios,
      ...(iosKey
        ? { config: { ...(base.ios?.config || {}), googleMapsApiKey: iosKey } }
        : {}),
    },
  }
}
