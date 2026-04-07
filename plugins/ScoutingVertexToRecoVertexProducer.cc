#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Scouting/interface/Run3ScoutingVertex.h"
#include "DataFormats/VertexReco/interface/Vertex.h"

#include <memory>
#include <vector>

class ScoutingVertexToRecoVertexProducer : public edm::one::EDProducer<> {
public:
  explicit ScoutingVertexToRecoVertexProducer(const edm::ParameterSet& iConfig)
      : srcToken_(consumes<std::vector<Run3ScoutingVertex>>(iConfig.getParameter<edm::InputTag>("src"))) {
    produces<reco::VertexCollection>();
  }

  void produce(edm::Event& iEvent, const edm::EventSetup&) override {
    edm::Handle<std::vector<Run3ScoutingVertex>> src;
    iEvent.getByToken(srcToken_, src);

    auto out = std::make_unique<reco::VertexCollection>();
    out->reserve(src->size());

    for (const auto& vtx : *src) {
      if (!vtx.isValidVtx()) {
        continue;
      }

      reco::Vertex::Error err;
      err(0, 0) = 0.0;
      err(0, 1) = 0.0;
      err(0, 2) = 0.0;
      err(1, 0) = 0.0;
      err(1, 1) = 0.0;
      err(1, 2) = 0.0;
      err(2, 0) = 0.0;
      err(2, 1) = 0.0;
      err(2, 2) = 0.0;
      err(0, 0) = vtx.xError() * vtx.xError();
      err(1, 1) = vtx.yError() * vtx.yError();
      err(2, 2) = vtx.zError() * vtx.zError();

      reco::Vertex recoVtx(reco::Vertex::Point(vtx.x(), vtx.y(), vtx.z()),
                           err,
                           vtx.chi2(),
                           vtx.ndof(),
                           vtx.tracksSize());
      out->push_back(recoVtx);
    }

    iEvent.put(std::move(out));
  }

private:
  edm::EDGetTokenT<std::vector<Run3ScoutingVertex>> srcToken_;
};

DEFINE_FWK_MODULE(ScoutingVertexToRecoVertexProducer);
