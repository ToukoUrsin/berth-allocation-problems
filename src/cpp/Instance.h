#ifndef INSTANCE_H
#define INSTANCE_H

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <filesystem>
#include <iterator>
#include <map>
#include <numeric>
#include <optional>
#include <ranges>
#include <string>
#include <utility>
#include <vector>

#include <json.hpp>

namespace {
    std::size_t scale_and_round_down(std::size_t x, double factor) {
        return static_cast<std::size_t>(std::floor(static_cast<double>(x) / factor));
    }

    std::size_t scale_and_round_up(std::size_t x, double factor) {
        return static_cast<std::size_t>(std::ceil(static_cast<double>(x) / factor));
    }
}

namespace bap {

    enum class HandlingAttribute {
        Fix,
        Pos
    };

    enum class SpatialAttribute {
        Discrete,
        Hybrid
    };

    enum class TemporalAttribute {
        Static,
        Dynamic
    };

    enum class ObjectiveFunctionAttribute {
        MaxCompl,
        SumWaitingHandling,
        WeightedSumWaitingHandling
    };

    struct Instance {
        std::filesystem::path path;
        std::string name;

        HandlingAttribute handling_attribute;
        SpatialAttribute spatial_attribute;
        TemporalAttribute temporal_attribute;
        ObjectiveFunctionAttribute objective_function_attribute;

        std::size_t n_periods;
        std::size_t n_ships;
        std::size_t n_berths;

    private:
        void determine_attributes(const nlohmann::json& data) {
            if(data.contains("arrival_time")) {
                temporal_attribute = TemporalAttribute::Dynamic;
            } else {
                temporal_attribute = TemporalAttribute::Static;
            }

            if(data.contains("ship_len")) {
                if(not data.contains("berth_len")) {
                    throw std::runtime_error("Instance " + path.filename().string() + " has ship_len but not berth_len attribute.");
                }

                spatial_attribute = SpatialAttribute::Hybrid;
            } else {
                if(data.contains("berth_len")) {
                    throw std::runtime_error("Instance " + path.filename().string() + " has berth_len but not ship_len attribute.");
                }

                spatial_attribute = SpatialAttribute::Discrete;
            }

            if(not data.contains("handling_time")) {
                throw std::runtime_error("Instance " + path.filename().string() + " does not have a handling_time attribute.");
            }

            if(data["handling_time"][0].is_number()) {
                handling_attribute = HandlingAttribute::Fix;
            } else if(data["handling_time"][0].is_array()) {
                handling_attribute = HandlingAttribute::Pos;
            } else {
                throw std::runtime_error("Wrong format for handling_time in " + path.filename().string());
            }

            if(data.contains("objective_function") and data["objective_function"].is_string()) {
                if(data["objective_function"] == "MaxCompl") {
                    objective_function_attribute = ObjectiveFunctionAttribute::MaxCompl;
                } else if(data["objective_function"] == "SumWaitingHandling") {
                    objective_function_attribute = ObjectiveFunctionAttribute::SumWaitingHandling;
                } else if(data["objective_function"] == "WeightedSumWaitingHandling") {
                    objective_function_attribute = ObjectiveFunctionAttribute::WeightedSumWaitingHandling;
                } else {
                    throw std::runtime_error(
                            "Invalid objective function " +
                            data["objective_function"].get<std::string>() +
                            " in " +
                            path.filename().string());
                }
            } else {
                if(data.contains("ship_importance")) {
                    objective_function_attribute = ObjectiveFunctionAttribute::WeightedSumWaitingHandling;
                } else {
                    objective_function_attribute = ObjectiveFunctionAttribute::MaxCompl;
                }
            }
        }

        std::optional<std::vector<std::size_t>> _arrival_time;
        std::optional<std::vector<std::size_t>> _handling_time_fix;
        std::optional<std::map<std::pair<std::size_t, std::size_t>, std::size_t>> _handling_time_pos;
        std::optional<std::vector<double>> _ship_len;
        std::optional<std::vector<double>> _berth_len;
        std::optional<std::vector<double>> _ship_importance;

    public:
        explicit Instance(std::filesystem::path path) {
            std::ifstream file{path};

            if(file.fail()) {
                throw std::runtime_error("Cannot open file " + path.string());
            }

            auto data = nlohmann::json::parse(file);

            n_periods = data["n_periods"];
            n_ships = data["n_ships"];
            n_berths = data["n_berths"];

            determine_attributes(data);

            if(temporal_attribute == TemporalAttribute::Dynamic) {
                _arrival_time = data["arrival_time"];
            }

            if(handling_attribute == HandlingAttribute::Fix) {
                _handling_time_fix = data["handling_time"];
            }

            if(handling_attribute == HandlingAttribute::Pos) {
                _handling_time_pos = {};

                const auto& ht = data["handling_time"];

                assert(ht.size() == n_ships);

                for(auto ship_idx = 0u; ship_idx < n_ships; ++ship_idx) {
                    assert(ht[ship_idx].size() == n_berths);

                    for(auto berth_idx = 0u; berth_idx < n_berths; ++berth_idx) {
                        (*_handling_time_pos)[{ship_idx, berth_idx}] = ht[ship_idx][berth_idx];
                    }
                }
            }

            if(spatial_attribute == SpatialAttribute::Hybrid) {
                _ship_len = data["ship_len"];
                _berth_len = data["berth_len"];
            }

            if(objective_function_attribute == ObjectiveFunctionAttribute::WeightedSumWaitingHandling) {
                _ship_importance = data["ship_importance"];
            }
        }

        std::size_t arrival_time(std::size_t ship) const {
            if(temporal_attribute == TemporalAttribute::Dynamic) {
                assert(_arrival_time);
                return _arrival_time->at(ship);
            }

            throw std::runtime_error("No arrival time when temporal attribute is not Dynamic.");
        }

        std::size_t handling_time(std::size_t ship) const {
            if(handling_attribute == HandlingAttribute::Fix) {
                assert(_handling_time_fix);
                return _handling_time_fix->at(ship);
            }

            throw std::runtime_error("No handling time as a funtion of the ship only when handling attribute is not Fix.");
        }

        std::size_t handling_time(std::size_t ship, std::size_t berth) const {
            if(handling_attribute == HandlingAttribute::Pos) {
                assert(_handling_time_pos);
                return _handling_time_pos->at({ship, berth});
            }

            throw std::runtime_error("No handling time as a function of both ship and berth when handling time is not Pos.");
        }

        double ship_len(std::size_t ship) const {
            if(spatial_attribute == SpatialAttribute::Hybrid) {
                assert(_ship_len);
                return _ship_len->at(ship);
            }

            throw std::runtime_error("No ship length when spatial attribute is not Hybrid.");
        }

        double berth_len(std::size_t ship) const {
            if(spatial_attribute == SpatialAttribute::Hybrid) {
                assert(_berth_len);
                return _berth_len->at(ship);
            }

            throw std::runtime_error("No berth length when spatial attribute is not Hybrid.");
        }

        double quay_len() const {
            if(spatial_attribute == SpatialAttribute::Hybrid) {
                return std::reduce(_berth_len->begin(), _berth_len->end());
            } else {
                return static_cast<double>(n_berths);
            }
        }

        double berth_start(std::size_t berth) const {
            if(spatial_attribute == SpatialAttribute::Hybrid) {
                if(berth == 0u) {
                    return 0.0;
                }

                return std::reduce(_berth_len->begin(), _berth_len->begin() + (berth - 1u));
            } else {
                throw std::runtime_error("No berth start when spatial attribute is not Hybrid.");
            }
        }

        double ship_importance(std::size_t ship) const {
            if(objective_function_attribute == ObjectiveFunctionAttribute::WeightedSumWaitingHandling) {
                assert(_ship_importance);
                return _ship_importance->at(ship);
            }

            throw std::runtime_error("No ship importance when obj func attribute is not a weighted sum.");
        }

        auto ships() const {
            return std::views::iota(std::size_t{0u}, n_ships + 1u);
        }

        auto periods() const {
            return std::views::iota(std::size_t{0u}, n_periods + 1u);
        }

        auto berths() const {
            return std::views::iota(std::size_t{0u}, n_berths + 1u);
        }

        Instance rescale_conservative(double factor) const {
            Instance newi = *this;

            newi.n_periods = scale_and_round_down(newi.n_periods, factor);

            if(temporal_attribute == TemporalAttribute::Dynamic) {
                assert(newi._arrival_time);
                auto& at = *newi._arrival_time;

                std::ranges::transform(at, at.begin(),
                                    [&] (auto a) { return scale_and_round_up(a, factor); });
            }

            if(handling_attribute == HandlingAttribute::Fix) {
                assert(newi._handling_time_fix);
                auto& ht = *newi._handling_time_fix;

                std::ranges::transform(ht, ht.begin(),
                                    [&] (auto h) { return scale_and_round_up(h, factor); });
            } else if(handling_attribute == HandlingAttribute::Pos) {
                assert(newi._handling_time_pos);
                auto& ht = *newi._handling_time_pos;

                std::transform(ht.begin(), ht.end(), std::inserter(ht, ht.end()), [factor] (auto kv) {
                    return {kv.first, scale_and_round_up(kv.second, factor)};
                });
            }

            return newi;
        }

        Instance rescale_aggressive(double factor) const {
            Instance newi = *this;

            newi.n_periods = scale_and_round_up(newi.n_periods, factor);

            if(temporal_attribute == TemporalAttribute::Dynamic) {
                assert(newi._arrival_time);
                auto& at = *newi._arrival_time;

                std::ranges::transform(at, at.begin(),
                                    [&] (auto a) { return scale_and_round_down(a, factor); });
            }

            if(handling_attribute == HandlingAttribute::Fix) {
                assert(newi._handling_time_fix);
                auto& ht = *newi._handling_time_fix;

                std::ranges::transform(ht, ht.begin(),
                                    [&] (auto h) { return scale_and_round_down(h, factor); });
            } else if(handling_attribute == HandlingAttribute::Pos) {
                assert(newi._handling_time_pos);
                auto& ht = *newi._handling_time_pos;

                std::transform(ht.begin(), ht.end(), std::inserter(ht, ht.end()), [factor] (auto kv) {
                    return {kv.first, scale_and_round_down(kv.second, factor)};
                });
            }

            return newi;
        }
    };

} // bap

#endif //INSTANCE_H
