import React, { useState } from 'react';
import { StyleSheet, TextInput, View, Text, TouchableOpacity, ActivityIndicator, Alert, ScrollView } from 'react-native';
import { analyzeRepo, getUseCases, getRepoExplanation } from '../../src/api/client';

export default function HomeScreen() {
  const [url, setUrl] = useState('https://github.com/pallets/flask');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [useCases, setUseCases] = useState<any>(null);
  const [repoExplanation, setRepoExplanation] = useState<any>(null);

  const handleAnalyze = async () => {
    if (!url) return;
    setLoading(true);
    setResult(null);
    setUseCases(null);
    setRepoExplanation(null);
    try {
      const data = await analyzeRepo(url);
      setResult(data);
      
      try {
        const cases = await getUseCases(data.id);
        setUseCases(cases);
      } catch(e) {
        console.warn('Use cases omitted');
      }

      try {
        const expl = await getRepoExplanation(data.id);
        setRepoExplanation(expl);
      } catch(e) {
        console.warn('Repo explanation omitted');
      }

      Alert.alert('Success', 'Repository analyzed successfully!');
    } catch (error: any) {
      console.error(error);
      Alert.alert('Error', error.response?.data?.detail || error.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Repo Analyzer 🚀</Text>
      <Text style={styles.subtitle}>Enter a GitHub URL to dissect its architecture using AI.</Text>

      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder="https://github.com/someone/repo"
          placeholderTextColor="#666"
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>

      <TouchableOpacity 
        style={[styles.button, loading && styles.buttonDisabled]} 
        onPress={handleAnalyze} 
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Analyze Repository</Text>
        )}
      </TouchableOpacity>

      {result && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Result for {result.repo_name}</Text>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Total Files:</Text>
            <Text style={styles.statValue}>{result.total_files}</Text>
          </View>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Total Classes:</Text>
            <Text style={styles.statValue}>{result.total_classes}</Text>
          </View>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Total Functions:</Text>
            <Text style={styles.statValue}>{result.total_functions}</Text>
          </View>
        </View>
      )}

      {repoExplanation && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Architecture Insight 🧠</Text>
          <Text style={styles.explanationText}>{repoExplanation.explanation}</Text>
        </View>
      )}

      {useCases && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>System Actors 🎭</Text>
          {useCases.actors?.map((actor: string, i: number) => (
            <Text key={i} style={styles.listItem}>• {actor}</Text>
          ))}
          
          <Text style={[styles.cardTitle, {marginTop: 16}]}>Extracted Use Cases ⚙️</Text>
          {useCases.use_cases?.map((uc: string, i: number) => (
            <Text key={i} style={styles.listItem}>• {uc}</Text>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A', // Premium dark mode background
  },
  content: {
    padding: 24,
    paddingTop: 60,
  },
  title: {
    fontSize: 32,
    fontWeight: '800',
    color: '#F8FAFC',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#94A3B8',
    marginBottom: 32,
    lineHeight: 24,
  },
  inputContainer: {
    marginBottom: 24,
  },
  input: {
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 12,
    padding: 16,
    color: '#F8FAFC',
    fontSize: 16,
  },
  button: {
    backgroundColor: '#3B82F6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#3B82F6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  card: {
    marginTop: 32,
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#F8FAFC',
    marginBottom: 16,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  statLabel: {
    fontSize: 16,
    color: '#94A3B8',
  },
  statValue: {
    fontSize: 16,
    color: '#38BDF8',
    fontWeight: 'bold',
  },
  explanationText: {
    fontSize: 14,
    color: '#E2E8F0',
    lineHeight: 22,
  },
  listItem: {
    fontSize: 14,
    color: '#CBD5E1',
    lineHeight: 22,
    marginBottom: 4,
  },
});
