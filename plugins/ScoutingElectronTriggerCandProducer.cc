#include "FWCore/Common/interface/TriggerNames.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"
#include "DataFormats/Common/interface/TriggerResults.h"
#include "DataFormats/HLTReco/interface/TriggerEvent.h"
#include "DataFormats/HLTReco/interface/TriggerObject.h"
#include "DataFormats/Math/interface/deltaR.h"
#include "DataFormats/PatCandidates/interface/TriggerObjectStandAlone.h"

#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;
using LeafCandidateRef = edm::Ref<LeafCandidateCollection>;
using LeafCandidateRefVector = edm::RefVector<LeafCandidateCollection>;

class ScoutingElectronTriggerCandProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingElectronTriggerCandProducer(const edm::ParameterSet& iConfig)
      : filterNames_(iConfig.getParameter<std::vector<std::string>>("filterNames")),
        inputs_(consumes<LeafCandidateRefVector>(iConfig.getParameter<edm::InputTag>("inputs"))),
        triggerBits_(consumes<edm::TriggerResults>(iConfig.getParameter<edm::InputTag>("bits"))),
        dRMatch_(iConfig.getParameter<double>("dR")),
        isAND_(iConfig.getParameter<bool>("isAND")),
        useTriggerEvent_(iConfig.getParameter<bool>("useTriggerEvent")) {
    const auto objects = iConfig.getParameter<edm::InputTag>("objects");
    if (useTriggerEvent_) {
      triggerEvent_ = consumes<trigger::TriggerEvent>(objects);
    } else {
      triggerObjects_ = consumes<std::vector<pat::TriggerObjectStandAlone>>(objects);
    }
    produces<LeafCandidateRefVector>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<LeafCandidateRefVector> inputs;
    edm::Handle<edm::TriggerResults> triggerBits;
    iEvent.getByToken(inputs_, inputs);
    iEvent.getByToken(triggerBits_, triggerBits);

    auto out = std::make_unique<LeafCandidateRefVector>();
    if (!triggerBits.isValid()) {
      iEvent.put(std::move(out));
      return;
    }

    if (useTriggerEvent_) {
      edm::Handle<trigger::TriggerEvent> triggerEvent;
      iEvent.getByToken(triggerEvent_, triggerEvent);
      if (!triggerEvent.isValid()) {
        iEvent.put(std::move(out));
        return;
      }
      const trigger::TriggerObjectCollection& triggerObjects(triggerEvent->getObjects());

      for (size_t i = 0; i < inputs->size(); ++i) {
        const LeafCandidateRef ref = (*inputs)[i];
        bool saveObj = evaluateTriggerEvent(ref, triggerEvent.product(), triggerObjects);
        if (saveObj) {
          out->push_back(ref);
        }
      }
    } else {
      edm::Handle<std::vector<pat::TriggerObjectStandAlone>> triggerObjects;
      iEvent.getByToken(triggerObjects_, triggerObjects);
      if (!triggerObjects.isValid()) {
        iEvent.put(std::move(out));
        return;
      }

      const edm::TriggerNames& triggerNames = iEvent.triggerNames(*triggerBits);
      for (size_t i = 0; i < inputs->size(); ++i) {
        const LeafCandidateRef ref = (*inputs)[i];
        bool saveObj = evaluatePatTrigger(ref, triggerObjects.product(), *triggerBits, triggerNames, iEvent);
        if (saveObj) {
          out->push_back(ref);
        }
      }
    }

    iEvent.put(std::move(out));
  }

private:
  bool evaluateTriggerEvent(const LeafCandidateRef& ref,
                            const trigger::TriggerEvent* triggerEvent,
                            const trigger::TriggerObjectCollection& triggerObjects) const {
    if (filterNames_.empty()) {
      return true;
    }

    bool saveObj = false;
    for (size_t f = 0; f < filterNames_.size(); ++f) {
      bool matched = false;
      unsigned int moduleFilterIndex = triggerEvent->sizeFilters();
      for (int i = 0; i < triggerEvent->sizeFilters(); ++i) {
        if (triggerEvent->filterLabel(i) == filterNames_[f]) {
          moduleFilterIndex = i;
          break;
        }
      }

      if (moduleFilterIndex < triggerEvent->sizeFilters()) {
        const trigger::Keys& keys = triggerEvent->filterKeys(moduleFilterIndex);
        for (const auto& key : keys) {
          const auto& obj = triggerObjects[key];
          if (reco::deltaR(ref->eta(), ref->phi(), obj.eta(), obj.phi()) < dRMatch_) {
            matched = true;
            break;
          }
        }
      }

      if (f == 0) {
        saveObj = matched;
      } else if (isAND_) {
        saveObj = saveObj && matched;
      } else {
        saveObj = saveObj || matched;
      }
    }

    return saveObj;
  }

  bool evaluatePatTrigger(const LeafCandidateRef& ref,
                          const std::vector<pat::TriggerObjectStandAlone>* triggerObjects,
                          const edm::TriggerResults& triggerBits,
                          const edm::TriggerNames& triggerNames,
                          edm::Event& iEvent) const {
    if (filterNames_.empty()) {
      return true;
    }

    bool saveObj = false;
    for (size_t f = 0; f < filterNames_.size(); ++f) {
      bool matched = false;
      for (auto obj : *triggerObjects) {
        obj.unpackPathNames(triggerNames);
        obj.unpackFilterLabels(iEvent, triggerBits);
        if (!obj.hasFilterLabel(filterNames_[f])) {
          continue;
        }
        if (reco::deltaR(ref->eta(), ref->phi(), obj.eta(), obj.phi()) < dRMatch_) {
          matched = true;
          break;
        }
      }

      if (f == 0) {
        saveObj = matched;
      } else if (isAND_) {
        saveObj = saveObj && matched;
      } else {
        saveObj = saveObj || matched;
      }
    }

    return saveObj;
  }

  std::vector<std::string> filterNames_;
  edm::EDGetTokenT<LeafCandidateRefVector> inputs_;
  edm::EDGetTokenT<edm::TriggerResults> triggerBits_;
  edm::EDGetTokenT<std::vector<pat::TriggerObjectStandAlone>> triggerObjects_;
  edm::EDGetTokenT<trigger::TriggerEvent> triggerEvent_;
  double dRMatch_;
  bool isAND_;
  bool useTriggerEvent_;
};

DEFINE_FWK_MODULE(ScoutingElectronTriggerCandProducer);
