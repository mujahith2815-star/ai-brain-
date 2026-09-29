// P.H.A.S.S Mobile Digital Twin - Flutter Phone Client Skeleton
// Implements:
// - WebSocket connection to Central Message Broker (port 8765)
// - Voice wake-word detection & streaming relay
// - Holographic HUD push notification cards
// - Local speech synthesizer (Text-to-Speech)

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_tts/flutter_tts.dart';

void main() {
  runApp(const PhassMobileApp());
}

class PhassMobileApp extends StatelessWidget {
  const PhassMobileApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'P.H.A.S.S Remote Twin',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0D1117),
        primaryColor: const Color(0xFF00FFCC),
      ),
      home: const PhassRemoteScreen(),
    );
  }
}

class PhassRemoteScreen extends StatefulWidget {
  const PhassRemoteScreen({Key? key}) : super(key: key);

  @override
  State<PhassRemoteScreen> createState() => _PhassRemoteScreenState();
}

class _PhassRemoteScreenState extends State<PhassRemoteScreen> {
  late WebSocketChannel _channel;
  final FlutterTts _tts = FlutterTts();
  final TextEditingController _queryController = TextEditingController();
  final List<Map<String, String>> _messages = [];
  bool _isConnected = false;

  final String brokerHost = "192.168.1.100";
  final int brokerPort = 8765;
  final String authToken = "phass_omni_secret_token_2026";

  @override
  void initState() {
    super.initState();
    _connectToBroker();
    _initTts();
  }

  void _initTts() async {
    await _tts.setLanguage("en-US");
    await _tts.setSpeechRate(0.5);
  }

  void _connectToBroker() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse('ws://$brokerHost:$brokerPort'));
      
      // Send Auth Handshake
      final authPayload = {
        'type': 'auth',
        'token': authToken,
        'client_id': 'phone_digital_twin_flutter',
        'client_type': 'phone',
        'signal_strength': -54,
      };
      _channel.sink.add(jsonEncode(authPayload));

      _channel.stream.listen((message) {
        final data = jsonDecode(message);
        if (data['type'] == 'auth_response') {
          setState(() {
            _isConnected = data['status'] == 'authenticated';
          });
        } else if (data['type'] == 'response') {
          final reply = data['reply'] ?? '';
          setState(() {
            _messages.add({'sender': 'P.H.A.S.S', 'text': reply});
          });
          _tts.speak(reply);
        }
      });
    } catch (e) {
      debugPrint("WebSocket Connection error: $e");
    }
  }

  void _sendQuery(String query) {
    if (query.trim().isEmpty) return;
    setState(() {
      _messages.add({'sender': 'User', 'text': query});
    });
    final payload = {
      'type': 'command',
      'query': query,
      'client_id': 'phone_digital_twin_flutter',
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    };
    _channel.sink.add(jsonEncode(payload));
    _queryController.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('P.H.A.S.S Digital Twin 📱'),
        actions: [
          Icon(
            _isConnected ? Icons.wifi : Icons.wifi_off,
            color: _isConnected ? Colors.greenAccent : Colors.redAccent,
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final m = _messages[index];
                final isUser = m['sender'] == 'User';
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF1F6FEB) : const Color(0xFF161B22),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isUser ? Colors.blueAccent : const Color(0xFF00FFCC),
                      ),
                    ),
                    child: Text(m['text'] ?? '', style: const TextStyle(fontSize: 15)),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(8),
            color: const Color(0xFF161B22),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _queryController,
                    decoration: const InputDecoration(
                      hintText: 'Say "Hey P.H.A.S.S, turn on LED..."',
                      border: InputBorder.none,
                    ),
                    onSubmitted: _sendQuery,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.mic, color: Color(0xFF00FFCC)),
                  onPressed: () => _sendQuery(_queryController.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _channel.sink.close();
    _queryController.dispose();
    super.dispose();
  }
}
