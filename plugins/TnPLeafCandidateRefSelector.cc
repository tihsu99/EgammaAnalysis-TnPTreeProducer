#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "CommonTools/Utils/interface/StringCutObjectSelector.h"

#include "DataFormats/Candidate/interface/LeafCandidate.h"
#include "DataFormats/Common/interface/RefVector.h"

#include <vector>

using LeafCandidateCollection = std::vector<reco::LeafCandidate>;
using LeafCandidateRef = edm::Ref<LeafCandidateCollection>;
using LeafCandidateRefVector = edm::RefVector<LeafCandidateCollection>;

class TnPLeafCandidateRefSelector : public edm::one::EDProducer<> {
public:
  explicit TnPLeafCandidateRefSelector(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<LeafCandidateCollection>(iConfig.getParameter<edm::InputTag>("src"))),
        selector_(iConfig.getParameter<std::string>("cut")) {
    produces<LeafCandidateRefVector>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<LeafCandidateCollection> src;
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<LeafCandidateRefVector>();
    for (size_t i = 0; i < src->size(); ++i) {
      LeafCandidateRef ref(src, i);
      if (selector_(*ref)) {
        out->push_back(ref);
      }
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<LeafCandidateCollection> srcToken_;
  StringCutObjectSelector<reco::LeafCandidate> selector_;
};

DEFINE_FWK_MODULE(TnPLeafCandidateRefSelector);
