#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Common/interface/ValueMap.h"
#include "DataFormats/Math/interface/deltaPhi.h"
#include "DataFormats/Scouting/interface/Run3ScoutingElectron.h"

#include "EgammaAnalysis/TnPTreeProducer/plugins/WriteValueMap.h"

#include <cmath>
#include <limits>
#include <vector>

class Run3ScoutingElectronBestTrackProducer : public edm::one::EDProducer<> {
public:
  explicit Run3ScoutingElectronBestTrackProducer(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingElectron>>(iConfig.getParameter<edm::InputTag>("Run3ScoutingElectron"))),
        trackPtMin_(iConfig.getParameter<std::vector<double>>("TrackPtMin")),
        trackChi2OverNdofMax_(iConfig.getParameter<std::vector<double>>("TrackChi2OverNdofMax")),
        relativeEnergyDifferenceMax_(iConfig.getParameter<std::vector<double>>("RelativeEnergyDifferenceMax")),
        deltaPhiMax_(iConfig.getParameter<std::vector<double>>("DeltaPhiMax")) {
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTrackd0");
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTrackdz");
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTrackpt");
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTracketa");
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTrackphi");
    produces<edm::ValueMap<float>>("Run3ScoutingElectronTrackchi2overndf");
    produces<edm::ValueMap<int>>("Run3ScoutingElectronTrackcharge");
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingElectron>> src;
    iEvent.getByToken(srcToken_, src);

    std::vector<float> bestD0;
    std::vector<float> bestDz;
    std::vector<float> bestPt;
    std::vector<float> bestEta;
    std::vector<float> bestPhi;
    std::vector<float> bestChi2OverNdof;
    std::vector<int> bestCharge;

    bestD0.reserve(src->size());
    bestDz.reserve(src->size());
    bestPt.reserve(src->size());
    bestEta.reserve(src->size());
    bestPhi.reserve(src->size());
    bestChi2OverNdof.reserve(src->size());
    bestCharge.reserve(src->size());

    for (const auto& ele : *src) {
      const auto region = std::abs(ele.eta()) < 1.479 ? 0u : 1u;
      const auto bestIndex = findBestTrackIndex(ele, region);

      bestD0.push_back(readTrackValue(ele.trkd0(), bestIndex, 999999.f));
      bestDz.push_back(readTrackValue(ele.trkdz(), bestIndex, 999999.f));
      bestPt.push_back(readTrackValue(ele.trkpt(), bestIndex, -1.f));
      bestEta.push_back(readTrackValue(ele.trketa(), bestIndex, 999999.f));
      bestPhi.push_back(readTrackValue(ele.trkphi(), bestIndex, 999999.f));
      bestChi2OverNdof.push_back(readTrackValue(ele.trkchi2overndf(), bestIndex, 999999.f));
      bestCharge.push_back(readTrackValue(ele.trkcharge(), bestIndex, 0));
    }

    writeValueMap(iEvent, src, bestD0, "Run3ScoutingElectronTrackd0");
    writeValueMap(iEvent, src, bestDz, "Run3ScoutingElectronTrackdz");
    writeValueMap(iEvent, src, bestPt, "Run3ScoutingElectronTrackpt");
    writeValueMap(iEvent, src, bestEta, "Run3ScoutingElectronTracketa");
    writeValueMap(iEvent, src, bestPhi, "Run3ScoutingElectronTrackphi");
    writeValueMap(iEvent, src, bestChi2OverNdof, "Run3ScoutingElectronTrackchi2overndf");
    writeValueMap(iEvent, src, bestCharge, "Run3ScoutingElectronTrackcharge");
  }

private:
  template <typename T>
  T readTrackValue(const std::vector<T>& values, size_t index, T fallback) const {
    return index < values.size() ? values[index] : fallback;
  }

  size_t findBestTrackIndex(const Run3ScoutingElectron& ele, unsigned int region) const {
    const auto& trkPt = ele.trkpt();
    const auto& trkPhi = ele.trkphi();
    const auto& trkChi2 = ele.trkchi2overndf();

    if (trkPt.empty()) {
      return invalidIndex();
    }

    const double ptMin = threshold(trackPtMin_, region);
    const double chi2Max = threshold(trackChi2OverNdofMax_, region);
    const double relEDiffMax = threshold(relativeEnergyDifferenceMax_, region);
    const double dPhiMax = threshold(deltaPhiMax_, region);
    const double eleEnergyProxy = std::max(1.0, static_cast<double>(ele.pt()));

    size_t bestIndex = invalidIndex();
    double bestScore = std::numeric_limits<double>::max();

    for (size_t i = 0; i < trkPt.size(); ++i) {
      const double pt = trkPt[i];
      const double chi2 = i < trkChi2.size() ? trkChi2[i] : std::numeric_limits<double>::max();
      const double dPhi = i < trkPhi.size() ? std::abs(reco::deltaPhi(ele.phi(), trkPhi[i])) : std::numeric_limits<double>::max();
      const double relEDiff = std::abs(eleEnergyProxy - pt) / eleEnergyProxy;

      if (pt < ptMin) {
        continue;
      }
      if (chi2 > chi2Max) {
        continue;
      }
      if (relEDiff > relEDiffMax) {
        continue;
      }
      if (dPhi > dPhiMax) {
        continue;
      }

      const double score = dPhi + 0.1 * relEDiff + 0.01 * chi2;
      if (score < bestScore) {
        bestScore = score;
        bestIndex = i;
      }
    }

    return bestIndex == invalidIndex() ? 0u : bestIndex;
  }

  double threshold(const std::vector<double>& values, unsigned int region) const {
    if (values.empty()) {
      return 0.0;
    }
    return values[std::min<unsigned int>(region, values.size() - 1)];
  }

  size_t invalidIndex() const { return std::numeric_limits<size_t>::max(); }

  edm::EDGetTokenT<std::vector<Run3ScoutingElectron>> srcToken_;
  std::vector<double> trackPtMin_;
  std::vector<double> trackChi2OverNdofMax_;
  std::vector<double> relativeEnergyDifferenceMax_;
  std::vector<double> deltaPhiMax_;
};

DEFINE_FWK_MODULE(Run3ScoutingElectronBestTrackProducer);
