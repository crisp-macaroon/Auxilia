import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';

class RouteRiskScreen extends ConsumerStatefulWidget {
  const RouteRiskScreen({super.key});

  @override
  ConsumerState<RouteRiskScreen> createState() => _RouteRiskScreenState();
}

class _RouteRiskScreenState extends ConsumerState<RouteRiskScreen> {
  final MapController _mapController = MapController();
  LatLng? _currentLocation;
  LatLng? _deliveryLocation;

  List<LatLng> _path = [];
  List<Map<String, dynamic>> _incidents = [];
  double _riskScore = 0.0;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _getCurrentLocation();
  }

  Future<void> _getCurrentLocation() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    final position = await Geolocator.getCurrentPosition();
    setState(() {
      _currentLocation = LatLng(position.latitude, position.longitude);
      _mapController.move(_currentLocation!, 13.0);
    });
  }

  Future<void> _calculateRouteRisk() async {
    if (_currentLocation == null || _deliveryLocation == null) return;

    setState(() => _isLoading = true);
    try {
      final riderId = await ref.read(currentRiderIdProvider.future);
      if (riderId == null) return;

      final api = ref.read(apiServiceProvider);
      final response = await api.postJson('/riders/$riderId/route-risk', {
        'rider_latitude': _currentLocation!.latitude,
        'rider_longitude': _currentLocation!.longitude,
        'delivery_latitude': _deliveryLocation!.latitude,
        'delivery_longitude': _deliveryLocation!.longitude,
      });

      setState(() {
        _path = (response['path_coordinates'] as List)
            .map(
              (p) => LatLng((p[0] as num).toDouble(), (p[1] as num).toDouble()),
            )
            .toList();
        _incidents = List<Map<String, dynamic>>.from(response['incidents']);
        _riskScore = (response['overall_risk_score'] as num).toDouble();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to calculate route risk: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Route Risk Analysis')),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter:
                  _currentLocation ??
                  const LatLng(19.0760, 72.8777), // Mumbai default
              initialZoom: 13.0,
              onTap: (tapPosition, point) {
                setState(() => _deliveryLocation = point);
              },
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.auxilia.rider',
              ),
              if (_path.isNotEmpty)
                PolylineLayer(
                  polylines: [
                    Polyline(
                      points: _path,
                      color: AppColors.primary,
                      strokeWidth: 4.0,
                    ),
                  ],
                ),
              if (_incidents.isNotEmpty)
                CircleLayer(
                  circles: _incidents
                      .map(
                        (incident) => CircleMarker(
                          point: LatLng(
                            (incident['lat'] as num).toDouble(),
                            (incident['lon'] as num).toDouble(),
                          ),
                          color: Colors.red.withOpacity(
                            0.3 * (incident['severity'] as num).toDouble(),
                          ),
                          radius:
                              1000 * (incident['severity'] as num).toDouble(),
                          borderColor: Colors.red,
                          borderStrokeWidth: 2,
                        ),
                      )
                      .toList(),
                ),
              MarkerLayer(
                markers: [
                  if (_currentLocation != null)
                    Marker(
                      point: _currentLocation!,
                      width: 40,
                      height: 40,
                      child: const Icon(
                        Icons.motorcycle,
                        color: AppColors.primary,
                        size: 30,
                      ),
                    ),
                  if (_deliveryLocation != null)
                    Marker(
                      point: _deliveryLocation!,
                      width: 40,
                      height: 40,
                      child: const Icon(
                        Icons.location_on,
                        color: Colors.red,
                        size: 40,
                      ),
                    ),
                ],
              ),
            ],
          ),

          if (_deliveryLocation == null)
            Positioned(
              top: 16,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'Tap on the map to set delivery location',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ),

          if (_deliveryLocation != null)
            Positioned(
              bottom: 24,
              left: 16,
              right: 16,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_path.isNotEmpty)
                    Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(color: Colors.black12, blurRadius: 8),
                        ],
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Route Risk Score',
                                style: TextStyle(color: Colors.grey),
                              ),
                              Text(
                                '${(_riskScore * 100).toStringAsFixed(1)}%',
                                style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: _riskScore > 0.6
                                      ? Colors.red
                                      : _riskScore > 0.3
                                      ? Colors.orange
                                      : Colors.green,
                                ),
                              ),
                            ],
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              const Text(
                                'Incidents',
                                style: TextStyle(color: Colors.grey),
                              ),
                              Text(
                                '${_incidents.length}',
                                style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _calculateRouteRisk,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _isLoading
                          ? const CircularProgressIndicator(
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            )
                          : const Text(
                              'Analyze Route Risk',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.white,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
