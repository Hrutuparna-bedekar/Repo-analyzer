import React, { useState } from 'react';
import { 
  StyleSheet, TextInput, View, Text, TouchableOpacity, 
  ActivityIndicator, Alert, ScrollView, Dimensions,
  KeyboardAvoidingView, Platform
} from 'react-native';
import { useRouter } from 'expo-router';
import { analyzeRepo } from '../../src/api/client';
import PremiumBackground from '@/components/premium-background';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');
export default function HomeScreen() {
  const [url, setUrl] = useState('https://github.com/pallets/flask');
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const router = useRouter();
  const colorScheme = useColorScheme() ?? 'dark';
  const theme = Colors[colorScheme];

  const handleAnalyze = async () => {
    if (!url) return;
    setLoading(true);
    setLoadingStep('Initializing AI engines...');
    
    try {
      setLoadingStep('Cloning repository...');
      const data = await analyzeRepo(url);
      
      setLoadingStep('Finalizing architecture map...');
      setTimeout(() => {
        setLoading(false);
        router.push({
          pathname: '/analysis',
          params: { id: data.id, repo_name: data.repo_name }
        });
      }, 1000);

    } catch (error: any) {
      console.error(error);
      Alert.alert('Analysis Failed', error.response?.data?.detail || error.message || 'Something went wrong');
      setLoading(false);
    }
  };

  return (
    <PremiumBackground>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView 
          style={styles.container} 
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.heroSection}>
            <View style={styles.navHeader}>
              <View style={styles.logoRow}>
                <View style={styles.logoDot} />
                <Text style={styles.navTitle}>AI Repository Analyzer</Text>
              </View>
            </View>

            <View style={styles.heroContent}>
              <Text style={styles.heroH1}>Understand any codebase in seconds</Text>
              <Text style={styles.heroP}>
                Powerful AI-driven repository analysis and architecture visualization.
              </Text>
              
              <View style={styles.inputContainer}>
                <View style={styles.inputWrapper}>
                  <MaterialCommunityIcons name="github" color="#64748b" size={20} style={styles.inputIcon} />
                  <TextInput
                    style={styles.heroInput}
                    placeholder="Enter GitHub Repository URL"
                    placeholderTextColor="#64748b"
                    value={url}
                    onChangeText={setUrl}
                    autoCapitalize="none"
                    autoCorrect={false}
                  />
                </View>
                
                <TouchableOpacity 
                  style={[styles.heroButton, loading && styles.buttonDisabled]} 
                  onPress={handleAnalyze} 
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#05070f" size="small" />
                  ) : (
                    <>
                      <Text style={styles.heroButtonText}>Analyze Repository</Text>
                      <MaterialCommunityIcons name="arrow-right" color="#05070f" size={20} />
                    </>
                  )}
                </TouchableOpacity>
                
                {loading && (
                  <Text style={styles.loadingStepText}>{loadingStep}</Text>
                )}
              </View>
            </View>

            <View style={styles.featurePreview}>
              <View style={styles.featItem}>
                <MaterialCommunityIcons name="code-tags" color={theme.cyan} size={22} />
                <Text style={styles.featText}>Interactive Graph</Text>
              </View>
              <View style={styles.featItem}>
                <MaterialCommunityIcons name="console" color={theme.purple} size={22} />
                <Text style={styles.featText}>Logic Tracing</Text>
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </PremiumBackground>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingBottom: 40,
  },
  navHeader: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 20,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#00e5ff',
    shadowColor: '#00e5ff',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
  },
  navTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F8FAFC',
    letterSpacing: 0.5,
  },
  heroSection: {
    paddingHorizontal: 24,
    paddingTop: 40,
  },
  heroContent: {
    alignItems: 'center',
    marginTop: 20,
  },
  heroH1: {
    fontSize: 42,
    fontWeight: '900',
    color: '#F8FAFC',
    textAlign: 'center',
    lineHeight: 52,
    marginBottom: 20,
  },
  heroP: {
    fontSize: 16,
    color: '#94A3B8',
    textAlign: 'center',
    lineHeight: 26,
    marginBottom: 40,
    paddingHorizontal: 10,
  },
  inputContainer: {
    width: '100%',
    gap: 16,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(13, 17, 23, 0.8)',
    borderRadius: 16,
    paddingHorizontal: 16,
    height: 64,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  inputIcon: {
    marginRight: 12,
  },
  heroInput: {
    flex: 1,
    color: '#F8FAFC',
    fontSize: 16,
  },
  heroButton: {
    backgroundColor: '#00e5ff',
    height: 64,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    shadowColor: '#00e5ff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  heroButtonText: {
    color: '#05070f',
    fontSize: 18,
    fontWeight: '800',
  },
  loadingStepText: {
    color: '#00e5ff',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 8,
  },
  featurePreview: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 32,
    marginTop: 60,
  },
  featItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  featText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: '500',
  },
});
