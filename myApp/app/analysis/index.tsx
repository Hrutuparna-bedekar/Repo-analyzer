import React, { useEffect } from 'react';
import { StyleSheet, View, TouchableOpacity, Text, SafeAreaView, Platform, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { WebView } from 'react-native-webview';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const apiIp = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.105.64:8000';

export default function AnalysisScreen() {
  const { id, repo_name } = useLocalSearchParams();
  const router = useRouter();
  const webViewRef = React.useRef<WebView>(null);

  // Load the web UI directly to ensure 100% parity with the mobile web version
  const webUrl = `${apiIp}/?analysis_id=${id}`;

  useEffect(() => {
    console.log('[AnalysisScreen] Loading WebView URL:', webUrl);
  }, [webUrl]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <MaterialCommunityIcons name="arrow-left" color="#fff" size={24} />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle} numberOfLines={1}>{repo_name}</Text>
            <View style={styles.statusBadge}>
              <View style={styles.statusDot} />
              <Text style={styles.statusText}>Live View</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.iconBtn} onPress={() => webViewRef.current?.reload()}>
            <MaterialCommunityIcons name="refresh" color="#fff" size={24} />
          </TouchableOpacity>
        </View>

        <View style={styles.webContainer}>
          <WebView
            ref={webViewRef}
            source={{ uri: webUrl }}
            style={styles.webview}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            startInLoadingState={true}
            renderLoading={() => (
              <View style={styles.loading}>
                <ActivityIndicator color="#00e5ff" size="large" />
                <Text style={styles.loadingText}>Syncing with Analyzer...</Text>
              </View>
            )}
            allowsBackForwardNavigationGestures={true}
            backgroundColor="#05070f"
            onError={(syntheticEvent) => {
              const { nativeEvent } = syntheticEvent;
              console.warn('WebView error: ', nativeEvent);
            }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#05070f',
  },
  container: {
    flex: 1,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: '#05070f',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.05)',
    ...Platform.select({
      ios: { paddingTop: 0 },
      android: { paddingTop: 10 }
    })
  },
  backBtn: {
    padding: 8,
  },
  headerInfo: {
    flex: 1,
    marginLeft: 12,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#fff',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#00e5ff',
  },
  statusText: {
    fontSize: 10,
    color: '#00e5ff',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  iconBtn: {
    padding: 8,
  },
  webContainer: {
    flex: 1,
  },
  webview: {
    flex: 1,
    backgroundColor: '#05070f',
  },
  loading: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#05070f',
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 16,
    fontSize: 14,
    fontWeight: '600',
  },
});
